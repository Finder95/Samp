"""Bot client implementations and helpers for GTA:SA automation."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Protocol

from .tester import BotClient, BotScript, PlaybackEvent, PlaybackLog, ScriptAction


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
class ActionTranslator:
    """Translate high-level script actions into client-understood payloads."""

    chat_prefix: str = "CHAT "
    wait_token: str = "WAIT"
    teleport_token: str = "TELEPORT"
    key_token: str = "KEY"
    option_token: str = "OPTION"
    wait_for_token: str = "WAITFOR"
    macro_token: str = "MACRO"

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

    def __post_init__(self) -> None:
        if self.command_file is None:
            self.command_file = self.gta_directory / "bot_commands.txt"
        self.transport = FileCommandTransport(self.command_file)
        self._process: subprocess.Popen[str] | None = None
        self._runner = ScriptRunner(self.transport)

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

    def execute_script(self, script: BotScript) -> PlaybackLog:
        return self._runner.run(script)

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


@dataclass(slots=True)
class DummyBotClient(BotClient):
    """Utility bot for tests that records sent payloads without launching GTA."""

    name: str
    transport: CommandTransport
    runner: ScriptRunner | None = None
    connected_to: str | None = None
    executed_logs: list[PlaybackLog] = field(default_factory=list)
    connect_delay: float = 0.0

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


__all__ = [
    "CommandTransport",
    "FileCommandTransport",
    "BufferedCommandTransport",
    "ActionTranslator",
    "ScriptRunner",
    "WineSampClient",
    "DummyBotClient",
]

