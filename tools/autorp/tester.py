"""Framework for orchestrating automated in-game tests using GTA:SA clients."""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import time
from typing import Iterable, Protocol, Sequence


class BotClient(Protocol):
    """Minimal interface for a controllable GTA:SA client."""

    name: str

    def connect(self, server_address: str) -> None:
        """Connect the client to the provided SA-MP server."""

    def execute_script(self, script: "BotScript") -> "PlaybackLog | None":
        """Execute a scripted sequence inside the game world and optionally return a log."""

    def disconnect(self) -> None:
        """Disconnect the client from the server."""

    def client_log_monitors(self) -> Sequence["ClientLogMonitor"] | None:
        """Return monitors that can be used to assert client-side logs (optional)."""


@dataclass(slots=True)
class ScriptAction:
    """Normalised representation of a single action for the client player."""

    type: str
    payload: dict[str, object]
    delay: float = 0.0

    @property
    def command(self) -> str | None:
        value = self.payload.get("command")
        return str(value) if value is not None else None

    @property
    def message(self) -> str | None:
        value = self.payload.get("message")
        return str(value) if value is not None else None

    def serialise(self) -> dict[str, object]:
        data = {"type": self.type, **self.payload}
        if self.delay and "seconds" not in data:
            data["delay"] = self.delay
        return data


def _normalise_action(raw: dict[str, object]) -> ScriptAction:
    action_type = str(raw.get("type", "command"))
    payload = {key: value for key, value in raw.items() if key != "type"}
    delay = 0.0
    if action_type == "wait":
        seconds = payload.get("seconds", payload.get("value", 1.0))
        try:
            delay = float(seconds)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            delay = 1.0
    elif "delay" in payload:
        try:
            delay = float(payload.get("delay", 0))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            delay = 0.0
    return ScriptAction(type=action_type, payload=payload, delay=delay)


@dataclass(slots=True)
class BotScript:
    """A scripted list of high level actions executed by a bot."""

    description: str
    commands: tuple[str, ...] = field(default_factory=tuple)
    actions: tuple[dict[str, object], ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        return json.dumps(
            {
                "description": self.description,
                "commands": list(self.commands),
                "actions": [dict(action) for action in self.actions],
            }
        )

    @classmethod
    def from_json(cls, payload: str | bytes | bytearray) -> "BotScript":
        data = json.loads(payload)
        return cls(
            description=data.get("description", ""),
            commands=tuple(data.get("commands", ()) or ()),
            actions=tuple(data.get("actions", ()) or ()),
        )

    def iter_actions(self) -> Sequence[ScriptAction]:
        if self.actions:
            return tuple(_normalise_action(dict(raw)) for raw in self.actions)
        return tuple(ScriptAction(type="command", payload={"command": command}) for command in self.commands)


@dataclass(slots=True)
class PlaybackEvent:
    """Record of a single event during bot playback."""

    action: ScriptAction
    command_payloads: tuple[str, ...]
    timestamp: float


@dataclass(slots=True)
class PlaybackLog:
    """Lightweight execution log returned by clients after running a script."""

    script_description: str
    events: tuple[PlaybackEvent, ...]

    def commands_sent(self) -> list[str]:
        payloads: list[str] = []
        for event in self.events:
            payloads.extend(event.command_payloads)
        return payloads

    def to_json(self) -> str:
        return json.dumps(
            {
                "script_description": self.script_description,
                "events": [
                    {
                        "timestamp": event.timestamp,
                        "action": event.action.serialise(),
                        "payloads": list(event.command_payloads),
                    }
                    for event in self.events
                ],
            }
        )


@dataclass(slots=True)
class LogExpectationResult:
    """Result of waiting for a specific phrase in the server log."""

    phrase: str
    matched: bool


@dataclass(slots=True)
class ClientLogExpectation:
    """Expectation describing a phrase that should appear in a client side log."""

    client_name: str
    phrase: str
    log_name: str = "chatlog"
    timeout: float | None = None
    poll_interval: float = 0.5


@dataclass(slots=True)
class ClientLogExpectationResult:
    """Evaluation result for a client side log expectation."""

    client_name: str
    log_name: str
    phrase: str
    matched: bool


@dataclass(slots=True)
class ClientLogExportRequest:
    """Description of a client log that should be materialised as an artefact."""

    client_name: str
    log_name: str = "chatlog"
    target_path: Path | None = None
    include_full_log: bool = False


@dataclass(slots=True)
class ClientLogExportResult:
    """Result returned for each exported client log."""

    client_name: str
    log_name: str
    content: str
    target_path: Path | None = None


@dataclass(slots=True)
class ClientRunResult:
    """Result returned by the orchestrator for a single client."""

    client_name: str
    log: PlaybackLog | None
    playback_log_path: Path | None = None
    screenshots: tuple[Path, ...] = ()


@dataclass(slots=True)
class TestRunResult:
    """Summary of a completed orchestrated run."""

    script: BotScript
    client_results: tuple[ClientRunResult, ...]
    log_expectations: tuple[LogExpectationResult, ...] = ()
    client_log_expectations: tuple[ClientLogExpectationResult, ...] = ()
    server_log_excerpt: str | None = None
    server_log_path: Path | None = None
    client_log_exports: tuple[ClientLogExportResult, ...] = ()

    def successful_clients(self) -> list[str]:
        return [result.client_name for result in self.client_results if result.log is not None]

    def logs_satisfied(self) -> bool:
        return all(result.matched for result in self.log_expectations)


@dataclass(slots=True)
class BotRunContext:
    """Definition of a single orchestrated run including expectations."""

    script: BotScript
    client_names: tuple[str, ...] = ()
    expect_server_logs: tuple[str, ...] = ()
    log_timeout: float = 15.0
    iterations: int = 1
    wait_after: float = 0.0
    client_log_expectations: tuple[ClientLogExpectation, ...] = ()
    wait_before: float = 0.0
    record_playback_dir: Path | None = None
    capture_server_log: bool = False
    server_log_export: Path | None = None
    client_log_exports: tuple[ClientLogExportRequest, ...] = ()


class SampServerController:
    """Manage lifecycle of a local SA-MP server instance."""

    def __init__(
        self,
        package_dir: Path,
        executable: str | None = None,
        startup_phrase: str = "Started server on",
    ) -> None:
        self.package_dir = package_dir
        self.executable = executable or "samp-server"
        self.startup_phrase = startup_phrase
        self._process: subprocess.Popen[str] | None = None
        self._log_monitor = ServerLogMonitor(self.package_dir / "server_log.txt")

    @property
    def server_address(self) -> str:
        cfg_path = self.package_dir / "server.cfg"
        port = 7777
        if cfg_path.exists():
            for line in cfg_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith("port "):
                    try:
                        port = int(line.split()[1])
                    except (IndexError, ValueError):
                        port = 7777
                    break
        return f"127.0.0.1:{port}"

    def start(self) -> None:
        binary = Path(self.executable)
        if not binary.is_absolute():
            binary = self.package_dir / binary
        if not binary.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku wykonywalnego serwera: {binary}")
        self._log_monitor.mark()
        self._process = subprocess.Popen(
            [str(binary)],
            cwd=self.package_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def wait_until_ready(self, timeout: float = 20.0) -> bool:
        if self._process is None:
            raise RuntimeError("Serwer nie został uruchomiony")
        log_path = self.package_dir / "server_log.txt"
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(
                    f"Proces serwera zakończył się niespodziewanie: {self._process.returncode}"
                )
            if log_path.exists():
                content = log_path.read_text(encoding="utf-8", errors="ignore")
                if self.startup_phrase in content:
                    return True
            time.sleep(0.5)
        return False

    def stop(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    @contextmanager
    def running(self, timeout: float = 20.0):
        """Context manager starting the server for the duration of the block."""

        self.start()
        try:
            if not self.wait_until_ready(timeout=timeout):
                raise TimeoutError("Serwer SA-MP nie wystartował w oczekiwanym czasie")
            yield self
        finally:
            self.stop()

    @property
    def log_monitor(self) -> "ServerLogMonitor":
        return self._log_monitor


class TestOrchestrator:
    """High level orchestrator that runs scripts against a server."""

    def __init__(
        self,
        clients: Iterable[BotClient],
        scripts_dir: Path | None = None,
        server_controller: SampServerController | None = None,
    ) -> None:
        self.clients = list(clients)
        self._client_lookup = {client.name: client for client in self.clients}
        self.scripts_dir = scripts_dir or Path("tests/scripts")
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.server_controller = server_controller

    def register_script(self, script: BotScript) -> Path:
        """Persist script to disk for inspection or reuse."""
        target = self.scripts_dir / f"{script.description.replace(' ', '_')}.json"
        target.write_text(script.to_json(), encoding="utf-8")
        return target

    def _select_clients(self, client_names: Sequence[str] | None) -> list[BotClient]:
        if not client_names:
            return list(self.clients)
        selected: list[BotClient] = []
        for name in client_names:
            client = self._client_lookup.get(name)
            if client is None:
                raise KeyError(f"Brak klienta bota o nazwie {name}")
            selected.append(client)
        return selected

    def _run_on_clients(
        self,
        server_address: str,
        script: BotScript,
        selected_clients: Sequence[BotClient],
        record_dir: Path | None = None,
    ) -> list[ClientRunResult]:
        results: list[ClientRunResult] = []
        playback_target: Path | None = record_dir
        if playback_target is not None:
            playback_target.mkdir(parents=True, exist_ok=True)
        for client in selected_clients:
            client.connect(server_address)
            try:
                log = client.execute_script(script)
            finally:
                client.disconnect()
            playback_path: Path | None = None
            if playback_target is not None and log is not None:
                filename = (
                    f"{script.description.replace(' ', '_')}_{client.name}.json"
                    if script.description
                    else f"script_{client.name}.json"
                )
                playback_path = playback_target / filename
                playback_path.write_text(log.to_json(), encoding="utf-8")
            screenshots = tuple(getattr(client, "captured_screenshots", ()) or ())
            results.append(
                ClientRunResult(
                    client_name=client.name,
                    log=log,
                    playback_log_path=playback_path,
                    screenshots=screenshots,
                )
            )
        return results

    def _evaluate_expectations(
        self,
        expectations: Sequence[str],
        timeout: float,
        monitor: "ServerLogMonitor | None",
    ) -> tuple[LogExpectationResult, ...]:
        if not expectations:
            return ()
        if monitor is None:
            raise ValueError("Brak monitora logów serwera do weryfikacji oczekiwań")
        results: list[LogExpectationResult] = []
        for phrase in expectations:
            matched = monitor.wait_for(phrase, timeout=timeout)
            results.append(LogExpectationResult(phrase=phrase, matched=matched))
        return tuple(results)

    def _collect_client_monitors(
        self, selected_clients: Sequence[BotClient]
    ) -> dict[str, dict[str, "ClientLogMonitor"]]:
        lookup: dict[str, dict[str, ClientLogMonitor]] = {}
        for client in selected_clients:
            monitors = client.client_log_monitors()
            if not monitors:
                continue
            client_map: dict[str, ClientLogMonitor] = {}
            for monitor in monitors:
                monitor.mark()
                client_map[monitor.name] = monitor
            lookup[client.name] = client_map
        return lookup

    def _evaluate_client_expectations(
        self,
        expectations: Sequence[ClientLogExpectation],
        default_timeout: float,
        monitor_lookup: dict[str, dict[str, "ClientLogMonitor"]],
    ) -> tuple[ClientLogExpectationResult, ...]:
        if not expectations:
            return ()
        results: list[ClientLogExpectationResult] = []
        for expectation in expectations:
            client_monitors = monitor_lookup.get(expectation.client_name)
            monitor = None if client_monitors is None else client_monitors.get(expectation.log_name)
            timeout = expectation.timeout or default_timeout
            if monitor is None:
                results.append(
                    ClientLogExpectationResult(
                        client_name=expectation.client_name,
                        log_name=expectation.log_name,
                        phrase=expectation.phrase,
                        matched=False,
                    )
                )
                continue
            matched = monitor.wait_for(
                expectation.phrase,
                timeout=timeout,
                poll_interval=expectation.poll_interval,
            )
            results.append(
                ClientLogExpectationResult(
                    client_name=expectation.client_name,
                    log_name=expectation.log_name,
                    phrase=expectation.phrase,
                    matched=matched,
                )
            )
        return tuple(results)

    def _export_client_logs(
        self,
        requests: Sequence[ClientLogExportRequest],
        monitor_lookup: dict[str, dict[str, "ClientLogMonitor"]],
    ) -> tuple[ClientLogExportResult, ...]:
        if not requests:
            return ()
        results: list[ClientLogExportResult] = []
        for request in requests:
            client_monitors = monitor_lookup.get(request.client_name)
            monitor = None if client_monitors is None else client_monitors.get(request.log_name)
            if monitor is None:
                results.append(
                    ClientLogExportResult(
                        client_name=request.client_name,
                        log_name=request.log_name,
                        content="",
                        target_path=request.target_path,
                    )
                )
                continue
            content = monitor.collect_since_mark(include_full=request.include_full_log)
            path = request.target_path
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            results.append(
                ClientLogExportResult(
                    client_name=request.client_name,
                    log_name=request.log_name,
                    content=content,
                    target_path=path,
                )
            )
        return tuple(results)

    def run(
        self,
        script: BotScript,
        server_address: str | None = None,
        client_names: Sequence[str] | None = None,
        expect_server_logs: Sequence[str] | None = None,
        log_timeout: float = 15.0,
        client_log_expectations: Sequence[ClientLogExpectation] | None = None,
        record_playback_dir: Path | None = None,
        capture_server_log: bool = False,
        server_log_export: Path | None = None,
        client_log_exports: Sequence[ClientLogExportRequest] | None = None,
    ) -> TestRunResult:
        """Run the script across all configured clients."""

        selected_clients = self._select_clients(client_names)
        expectations = tuple(expect_server_logs or ())
        client_monitor_lookup = self._collect_client_monitors(selected_clients)
        client_expectations = tuple(client_log_expectations or ())
        client_export_requests = tuple(client_log_exports or ())
        client_export_results: tuple[ClientLogExportResult, ...]
        server_log_excerpt: str | None = None
        server_log_path: Path | None = None
        if server_address:
            results = self._run_on_clients(
                server_address, script, selected_clients, record_dir=record_playback_dir
            )
            log_expectations = self._evaluate_expectations(expectations, log_timeout, None)
            client_log_results = self._evaluate_client_expectations(
                client_expectations, log_timeout, client_monitor_lookup
            )
            client_export_results = self._export_client_logs(
                client_export_requests, client_monitor_lookup
            )
            return TestRunResult(
                script=script,
                client_results=tuple(results),
                log_expectations=log_expectations,
                client_log_expectations=client_log_results,
                server_log_excerpt=server_log_excerpt,
                server_log_path=server_log_path,
                client_log_exports=client_export_results,
            )

        if self.server_controller is None:
            raise ValueError("Brak kontrolera serwera oraz adresu — nie można uruchomić testu")

        with self.server_controller.running() as controller:
            monitor = controller.log_monitor
            monitor.mark()
            results = self._run_on_clients(
                controller.server_address,
                script,
                selected_clients,
                record_dir=record_playback_dir,
            )
            log_expectations = self._evaluate_expectations(expectations, log_timeout, monitor)
            client_log_results = self._evaluate_client_expectations(
                client_expectations, log_timeout, client_monitor_lookup
            )
            client_export_results = self._export_client_logs(
                client_export_requests, client_monitor_lookup
            )
            if monitor is not None and (capture_server_log or server_log_export is not None):
                excerpt = monitor.collect_since_mark(include_full=capture_server_log)
                server_log_excerpt = excerpt
                if server_log_export is not None:
                    server_log_export.parent.mkdir(parents=True, exist_ok=True)
                    server_log_export.write_text(excerpt, encoding="utf-8")
                    server_log_path = server_log_export
        return TestRunResult(
            script=script,
            client_results=tuple(results),
            log_expectations=log_expectations,
            client_log_expectations=client_log_results,
            server_log_excerpt=server_log_excerpt,
            server_log_path=server_log_path,
            client_log_exports=client_export_results,
        )

    def run_suite(
        self,
        runs: Sequence[BotRunContext],
        server_address: str | None = None,
    ) -> list[TestRunResult]:
        """Execute a sequence of orchestrated runs, respecting iterations and waits."""

        results: list[TestRunResult] = []
        for run in runs:
            for iteration in range(max(1, run.iterations)):
                if run.wait_before > 0 and iteration == 0:
                    time.sleep(run.wait_before)
                result = self.run(
                    run.script,
                    server_address=server_address,
                    client_names=run.client_names,
                    expect_server_logs=run.expect_server_logs,
                    log_timeout=run.log_timeout,
                    client_log_expectations=run.client_log_expectations,
                    record_playback_dir=run.record_playback_dir,
                    capture_server_log=run.capture_server_log,
                    server_log_export=run.server_log_export,
                    client_log_exports=run.client_log_exports,
                )
                results.append(result)
                if run.wait_after > 0 and iteration + 1 < run.iterations:
                    time.sleep(run.wait_after)
        return results


TestOrchestrator.__test__ = False  # type: ignore[attr-defined]


__all__ = [
    "BotScript",
    "ScriptAction",
    "TestOrchestrator",
    "BotClient",
    "SampServerController",
    "PlaybackLog",
    "PlaybackEvent",
    "LogExpectationResult",
    "ClientLogExpectation",
    "ClientLogExpectationResult",
    "ClientLogExportRequest",
    "ClientLogExportResult",
    "ClientRunResult",
    "TestRunResult",
    "BotRunContext",
    "ServerLogMonitor",
    "ClientLogMonitor",
]


class ServerLogMonitor:
    """Utility for tailing server_log.txt and searching for phrases."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._offset = 0
        self._mark_offset = 0

    def _read(self) -> str:
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8", errors="ignore")

    def snapshot(self) -> str:
        return self._read()

    def mark(self) -> None:
        content = self._read()
        self._offset = len(content)
        self._mark_offset = len(content)

    def wait_for(self, phrase: str, timeout: float = 10.0, poll_interval: float = 0.5) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            content = self._read()
            segment = content[self._offset :]
            if phrase in segment:
                self._offset = len(content)
                return True
            self._offset = len(content)
            time.sleep(poll_interval)
        return False

    def contains(self, phrase: str) -> bool:
        return phrase in self._read()

    def collect_since_mark(self, include_full: bool = False) -> str:
        content = self._read()
        if include_full:
            segment = content
        else:
            segment = content[self._mark_offset :]
        self._mark_offset = len(content)
        self._offset = len(content)
        return segment


@dataclass(slots=True)
class ClientLogMonitor:
    """Tail-like monitor for client side artefacts such as chatlogs."""

    client_name: str
    name: str
    log_path: Path
    encoding: str = "utf-8"
    _offset: int = 0
    _mark_offset: int = 0

    def _read(self) -> str:
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding=self.encoding, errors="ignore")

    def mark(self) -> None:
        content = self._read()
        self._offset = len(content)
        self._mark_offset = len(content)

    def wait_for(self, phrase: str, timeout: float = 10.0, poll_interval: float = 0.5) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            content = self._read()
            segment = content[self._offset :]
            if phrase in segment:
                self._offset = len(content)
                return True
            self._offset = len(content)
            time.sleep(poll_interval)
        return False

    def contains(self, phrase: str) -> bool:
        return phrase in self._read()

    def collect_since_mark(self, include_full: bool = False) -> str:
        content = self._read()
        if include_full:
            segment = content
        else:
            segment = content[self._mark_offset :]
        self._mark_offset = len(content)
        self._offset = len(content)
        return segment
