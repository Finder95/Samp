"""Bot client implementations and helpers for GTA:SA automation."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Protocol

from .tester import (
    BotClient,
    BotScript,
    ClientLogMonitor,
    PlaybackEvent,
    PlaybackLog,
    ScriptAction,
)


class CommandTransport(Protocol):
    """Abstraction responsible for delivering commands to the game client."""

    def send(self, payload: str) -> None:
        """Send a single payload to the underlying transport."""

    def flush(self) -> None:
        """Ensure all pending data is visible to the consumer."""


@dataclass(slots=True)
class FileCommandTransport:
    """Simple transport that appends commands to a text file watched by the client."""

    path: Path
    separator: str = "\n"
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding=self.encoding)

    def send(self, payload: str) -> None:
        with self.path.open("a", encoding=self.encoding) as handle:
            handle.write(payload + self.separator)

    def flush(self) -> None:
        os.utime(self.path, None)


@dataclass(slots=True)
class BufferedCommandTransport:
    """In-memory transport useful for tests and dry-runs."""

    buffer: list[str] = field(default_factory=list)

    def send(self, payload: str) -> None:
        self.buffer.append(payload)

    def flush(self) -> None:  # pragma: no cover - noop flush
        return

    def clear(self) -> None:
        self.buffer.clear()

    def extend(self, values: Iterable[str]) -> None:
        self.buffer.extend(values)


@dataclass(slots=True)
class WineWindowInteractor:
    """Control Wine windows through xdotool to drive the SA-MP client."""

    window_title: str = "San Andreas Multiplayer"
    xdotool_binary: str = "xdotool"
    dry_run: bool = False
    dry_run_window_id: str = "0x1"
    executed_commands: list[list[str]] = field(default_factory=list)

    def _invoke(self, *args: str, capture_output: bool = False):
        command = [self.xdotool_binary, *args]
        self.executed_commands.append(command)
        if self.dry_run:
            if capture_output:
                return type("Result", (), {"stdout": self.dry_run_window_id})()
            return None
        return subprocess.run(command, check=True, text=True, capture_output=capture_output)

    def _search_window(self, title: str | None = None) -> str | None:
        result = self._invoke("search", "--name", title or self.window_title, capture_output=True)
        if result is None:
            return self.dry_run_window_id
        output = str(result.stdout or "").strip().splitlines()
        return output[0] if output else None

    def focus(self, title: str | None = None) -> None:
        window_id = self._search_window(title)
        if not window_id:
            raise RuntimeError("Nie znaleziono okna klienta SA-MP do aktywacji")
        self._invoke("windowactivate", "--sync", window_id)
        self._invoke("windowraise", window_id)

    def type_text(self, text: str) -> None:
        if not text:
            return
        self._invoke("type", "--delay", "25", text)

    def mouse_move(self, x: float, y: float, mode: str = "absolute", duration: float = 0.0) -> None:
        if mode == "relative":
            self._invoke("mousemove_relative", "--", str(int(x)), str(int(y)))
        else:
            args = ["mousemove", "--sync", str(int(x)), str(int(y))]
            if duration > 0:
                args.extend(["--delay", str(int(duration * 1000))])
            self._invoke(*args)

    def mouse_click(self, button: str, state: str = "click") -> None:
        normalized = button.lower()
        mapping = {"left": "1", "right": "3", "middle": "2"}
        target = mapping.get(normalized, normalized)
        if state in {"down", "hold"}:
            self._invoke("mousedown", target)
        elif state in {"up", "release"}:
            self._invoke("mouseup", target)
        elif state == "double":
            self._invoke("click", "--repeat", "2", target)
        else:
            self._invoke("click", target)

@dataclass(slots=True)
class ActionTranslator:
    """Translate high-level script actions into client-understood payloads."""

    chat_prefix: str = "CHAT "
    wait_token: str = "WAIT"
    teleport_token: str = "TELEPORT"
    key_token: str = "KEY"
    option_token: str = "OPTION"
    wait_for_token: str = "WAITFOR"
    macro_token: str = "MACRO"
    type_token: str = "TYPE"
    focus_token: str = "FOCUS"
    mouse_token: str = "MOUSE"
    mouse_click_token: str = "MOUSECLICK"
    screenshot_token: str = "SCREENSHOT"
    config_token: str = "CONFIG"

    def translate(self, action: ScriptAction) -> tuple[str, ...]:
        if action.type == "chat" and action.message is not None:
            return (f"{self.chat_prefix}{action.message}",)
        if action.type == "wait":
            return (f"{self.wait_token}:{action.delay}",)
        if action.type == "teleport":
            coords = (
                float(action.payload.get("x", 0.0)),
                float(action.payload.get("y", 0.0)),
                float(action.payload.get("z", 0.0)),
            )
            interior = int(action.payload.get("interior", 0))
            world = int(action.payload.get("world", 0))
            coord_string = ",".join(str(value) for value in coords)
            return (f"{self.teleport_token}:{coord_string}:{interior}:{world}",)
        if action.type in {"key", "keypress"}:
            key = str(action.payload.get("key", "")).strip()
            if not key:
                raise ValueError("Brak klawisza do wysłania w akcji keypress")
            state = str(action.payload.get("state", "press")).lower()
            key = key.upper()
            if state == "press":
                return (
                    f"{self.key_token}:{key}:down",
                    f"{self.key_token}:{key}:up",
                )
            if state in {"down", "hold"}:
                return (f"{self.key_token}:{key}:down",)
            if state in {"up", "release"}:
                return (f"{self.key_token}:{key}:up",)
            raise ValueError(f"Nieobsługiwany stan klawisza: {state}")
        if action.type == "option":
            name = str(action.payload.get("name", action.payload.get("key", "")))
            value = action.payload.get("value")
            if not name:
                raise ValueError("Opcja klienta wymaga nazwy")
            return (f"{self.option_token}:{name}={value}",)
        if action.type in {"sequence", "macro"}:
            commands = action.payload.get("commands") or action.payload.get("steps")
            if not isinstance(commands, (list, tuple)):
                raise ValueError("Makro wymaga listy komend")
            return tuple(str(entry) for entry in commands)
        if action.type == "wait_for":
            phrase = str(action.payload.get("phrase", action.payload.get("value", "")))
            timeout = float(action.payload.get("timeout", action.payload.get("seconds", 10.0)))
            return (f"{self.wait_for_token}:{timeout}:{phrase}",)
        if action.type == "focus_window":
            title = action.payload.get("title")
            if title:
                return (f"{self.focus_token}:{title}",)
            return (self.focus_token,)
        if action.type == "type_text":
            text = action.payload.get("text", action.payload.get("value"))
            if text is None:
                raise ValueError("Brak tekstu dla akcji type_text")
            return (f"{self.type_token}:{text}",)
        if action.type in {"mouse_move", "mouse"}:
            x = action.payload.get("x")
            y = action.payload.get("y")
            if x is None or y is None:
                raise ValueError("Akcja mouse_move wymaga współrzędnych x i y")
            mode = str(action.payload.get("mode", "absolute"))
            duration = float(action.payload.get("duration", 0.0))
            return (f"{self.mouse_token}:{mode}:{float(x)}:{float(y)}:{duration}",)
        if action.type in {"mouse_click", "click"}:
            button = str(action.payload.get("button", "left"))
            action_mode = str(action.payload.get("state", action.payload.get("mode", "click")))
            return (f"{self.mouse_click_token}:{button}:{action_mode}",)
        if action.type == "screenshot":
            name = str(action.payload.get("name", "capture"))
            target = action.payload.get("path") or action.payload.get("directory")
            if target:
                return (f"{self.screenshot_token}:{name}:{target}",)
            return (f"{self.screenshot_token}:{name}",)
        if action.type == "config":
            name = str(action.payload.get("name", action.payload.get("key", "")))
            if not name:
                raise ValueError("Akcja config wymaga nazwy parametru")
            value = action.payload.get("value")
            return (f"{self.config_token}:{name}={value}",)
        command = action.command or action.payload.get("value")
        if command is None:
            return (f"ACTION:{action.type}",)
        return (str(command),)


@dataclass(slots=True)
class ScriptRunner:
    """Execute BotScript objects using a transport and optional translator."""

    transport: CommandTransport
    translator: ActionTranslator = field(default_factory=ActionTranslator)
    sleep: Callable[[float], None] = time.sleep
    on_event: Callable[[PlaybackEvent], None] | None = None

    def run(self, script: BotScript) -> PlaybackLog:
        events: list[PlaybackEvent] = []
        for action in script.iter_actions():
            payloads = self.translator.translate(action)
            for payload in payloads:
                self.transport.send(payload)
            self.transport.flush()
            if action.delay > 0:
                self.sleep(action.delay)
            event = PlaybackEvent(
                action=action,
                command_payloads=payloads,
                timestamp=time.time(),
            )
            if self.on_event is not None:
                self.on_event(event)
            events.append(event)
        return PlaybackLog(script_description=script.description, events=tuple(events))


@dataclass(slots=True)
class WineSampClient(BotClient):
    """Launch and control the SA-MP client through Wine for automated tests."""

    name: str
    gta_directory: Path
    launcher: str = "samp.exe"
    wine_binary: str = "wine"
    command_file: Path | None = None
    dry_run: bool = False
    extra_env: dict[str, str] = field(default_factory=dict)
    connect_delay: float = 0.0
    reset_commands_on_connect: bool = True
    focus_window: bool = False
    window_title: str = "San Andreas Multiplayer"
    xdotool_binary: str = "xdotool"
    log_files: tuple[tuple[str, Path, str], ...] = ()
    chatlog_path: Path | None = None
    chatlog_encoding: str = "utf-8"
    setup_actions: tuple[dict[str, object], ...] = ()
    teardown_actions: tuple[dict[str, object], ...] = ()

    def __post_init__(self) -> None:
        if self.command_file is None:
            self.command_file = self.gta_directory / "bot_commands.txt"
        self.transport = FileCommandTransport(self.command_file)
        self._process: subprocess.Popen[str] | None = None
        self.translator = ActionTranslator()
        self._runner = ScriptRunner(self.transport, translator=self.translator)
        self._runner.on_event = self._handle_event
        self.window_interactor: WineWindowInteractor | None = None
        if self.focus_window:
            self.window_interactor = WineWindowInteractor(
                window_title=self.window_title,
                xdotool_binary=self.xdotool_binary,
                dry_run=self.dry_run,
            )
        self._client_log_monitors = self._build_log_monitors()
        self._setup_script = BotScript(description=f"setup:{self.name}", actions=self.setup_actions)
        self._teardown_script = BotScript(
            description=f"teardown:{self.name}", actions=self.teardown_actions
        ) if self.teardown_actions else None
        self.captured_screenshots: list[Path] = []

    def _reset_command_file(self) -> None:
        if self.command_file is not None:
            self.command_file.write_text("", encoding="utf-8")

    def _launch_process(self, server_address: str) -> None:
        launcher_path = Path(self.launcher)
        if not launcher_path.is_absolute():
            launcher_path = self.gta_directory / launcher_path
        if not launcher_path.exists() and not self.dry_run:
            raise FileNotFoundError(f"Nie znaleziono pliku klienta SA-MP: {launcher_path}")
        if self.dry_run:
            self._process = None
            return
        env = os.environ.copy()
        env.update(self.extra_env)
        args = [self.wine_binary, str(launcher_path), server_address]
        self._process = subprocess.Popen(args, cwd=self.gta_directory, env=env, text=True)

    def connect(self, server_address: str) -> None:
        if self.reset_commands_on_connect:
            self._reset_command_file()
        self._launch_process(server_address)
        if self.connect_delay > 0:
            time.sleep(self.connect_delay)
        if self.window_interactor is not None:
            try:
                self.window_interactor.focus()
            except RuntimeError:
                if not self.dry_run:
                    raise

    def execute_script(self, script: BotScript) -> PlaybackLog:
        if self.setup_actions:
            self._runner.run(self._setup_script)
        log = self._runner.run(script)
        if self.teardown_actions and self._teardown_script is not None:
            self._runner.run(self._teardown_script)
        return log

    def disconnect(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    def _build_log_monitors(self) -> tuple[ClientLogMonitor, ...]:
        entries: list[tuple[str, Path, str]] = list(self.log_files)
        chatlog = self.chatlog_path or self.gta_directory / "SAMP" / "chatlog.txt"
        if not any(name == "chatlog" for name, _, _ in entries):
            entries.append(("chatlog", chatlog, self.chatlog_encoding))
        monitors: list[ClientLogMonitor] = []
        for name, path, encoding in entries:
            resolved = path
            if not resolved.is_absolute():
                resolved = self.gta_directory / resolved
            resolved.parent.mkdir(parents=True, exist_ok=True)
            monitors.append(
                ClientLogMonitor(
                    client_name=self.name,
                    name=name,
                    log_path=resolved,
                    encoding=encoding,
                )
            )
        return tuple(monitors)

    def client_log_monitors(self) -> tuple[ClientLogMonitor, ...]:
        return self._client_log_monitors

    def _handle_event(self, event: PlaybackEvent) -> None:
        if self.window_interactor is None:
            return
        for payload in event.command_payloads:
            if payload.startswith(self.translator.focus_token):
                parts = payload.split(":", 1)
                title = parts[1] if len(parts) > 1 else None
                try:
                    self.window_interactor.focus(title or None)
                except RuntimeError:
                    if not self.dry_run:
                        raise
            elif payload.startswith(f"{self.translator.type_token}:"):
                text = payload.split(":", 1)[1]
                self.window_interactor.type_text(text)
            elif payload.startswith(f"{self.translator.mouse_token}:"):
                _, mode, x, y, duration = payload.split(":", 4)
                self.window_interactor.mouse_move(float(x), float(y), mode=mode, duration=float(duration))
            elif payload.startswith(f"{self.translator.mouse_click_token}:"):
                _, button, state = payload.split(":", 2)
                self.window_interactor.mouse_click(button, state)
            elif payload.startswith(f"{self.translator.screenshot_token}:"):
                parts = payload.split(":", 2)
                name = parts[1] if len(parts) > 1 else "capture"
                target = parts[2] if len(parts) > 2 else None
                path = Path(target) if target else self.gta_directory / f"{name}.png"
                if not path.is_absolute():
                    path = self.gta_directory / path
                self.captured_screenshots.append(path)


@dataclass(slots=True)
class DummyBotClient(BotClient):
    """Utility bot for tests that records sent payloads without launching GTA."""

    name: str
    transport: CommandTransport
    runner: ScriptRunner | None = None
    connected_to: str | None = None
    executed_logs: list[PlaybackLog] = field(default_factory=list)
    connect_delay: float = 0.0
    log_monitors: tuple[ClientLogMonitor, ...] = ()

    def __post_init__(self) -> None:
        if self.runner is None:
            self.runner = ScriptRunner(self.transport, sleep=lambda _: None)

    def connect(self, server_address: str) -> None:  # pragma: no cover - trivial
        self.connected_to = server_address
        if self.connect_delay > 0:
            time.sleep(self.connect_delay)

    def execute_script(self, script: BotScript) -> PlaybackLog:
        log = self.runner.run(script)
        self.executed_logs.append(log)
        return log

    def disconnect(self) -> None:  # pragma: no cover - trivial
        self.connected_to = None

    def client_log_monitors(self) -> tuple[ClientLogMonitor, ...]:  # pragma: no cover - trivial
        return self.log_monitors


__all__ = [
    "CommandTransport",
    "FileCommandTransport",
    "BufferedCommandTransport",
    "WineWindowInteractor",
    "ActionTranslator",
    "ScriptRunner",
    "WineSampClient",
    "DummyBotClient",
]

