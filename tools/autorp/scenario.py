"""Scenario helpers translating config bot definitions into scripts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .tester import BotScript


def _ensure_leading_slash(command: str) -> str:
    command = command.strip()
    if not command.startswith("/"):
        command = "/" + command
    return command


@dataclass(slots=True)
class ScenarioStep:
    """Normalised representation of a scenario step."""

    type: str
    payload: dict[str, object]

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioStep":
        if isinstance(data, str):
            return cls("command", {"command": _ensure_leading_slash(data)})
        if not isinstance(data, dict):
            raise TypeError(f"Unsupported scenario step type: {type(data)!r}")
        step_type = data.get("type") or data.get("action") or "command"
        payload: dict[str, object]
        if step_type == "command":
            value = data.get("value") or data.get("command") or ""
            payload = {"command": _ensure_leading_slash(str(value))}
        elif step_type == "chat":
            payload = {"message": str(data.get("message") or data.get("value") or "")}
        elif step_type == "wait":
            payload = {"seconds": float(data.get("seconds") or data.get("value") or 1.0)}
        elif step_type == "teleport":
            payload = {
                "x": float(data.get("x", 0.0)),
                "y": float(data.get("y", 0.0)),
                "z": float(data.get("z", 0.0)),
                "interior": int(data.get("interior", 0)),
                "world": int(data.get("world", 0)),
            }
        else:
            payload = {key: value for key, value in data.items() if key not in {"type", "action"}}
        return cls(step_type, payload)

    def to_command(self) -> str:
        if self.type == "command":
            return str(self.payload.get("command", ""))
        if self.type == "chat":
            return f"CHAT:{self.payload.get('message', '')}"
        if self.type == "wait":
            return f"WAIT:{self.payload.get('seconds', 1)}"
        if self.type == "teleport":
            coords = ",".join(str(self.payload.get(axis, 0)) for axis in ("x", "y", "z"))
            return f"TELEPORT:{coords}"
        return f"ACTION:{self.type}"

    def to_payload(self) -> dict[str, object]:
        return {"type": self.type, **self.payload}


@dataclass(slots=True)
class BotScenarioSpec:
    """Container describing a bot scenario parsed from config."""

    name: str
    description: str
    steps: Sequence[dict]

    def normalised_steps(self) -> list[ScenarioStep]:
        return [ScenarioStep.from_dict(step) for step in self.steps]

    def to_bot_script(self) -> BotScript:
        steps = self.normalised_steps()
        commands = tuple(step.to_command() for step in steps)
        actions = tuple(step.to_payload() for step in steps)
        return BotScript(description=self.description, commands=commands, actions=actions)


__all__ = ["ScenarioStep", "BotScenarioSpec"]
