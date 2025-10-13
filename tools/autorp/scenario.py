"""Scenario helpers translating config bot definitions into scripts."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, Mapping, Sequence

from .tester import BotScript


_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")


def _replace_placeholders(value: object, variables: Mapping[str, object]) -> object:
    """Recursively replace ``{{variable}}`` placeholders using provided variables."""

    if isinstance(value, str):
        def _substitute(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, ""))

        return _PLACEHOLDER_PATTERN.sub(_substitute, value)
    if isinstance(value, dict):
        return {key: _replace_placeholders(val, variables) for key, val in value.items()}
    if isinstance(value, list):
        return [_replace_placeholders(item, variables) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_placeholders(item, variables) for item in value)
    return value


@dataclass(slots=True)
class BotScriptMacro:
    """Reusable snippet of scenario steps that can accept parameters."""

    name: str
    steps: tuple[dict[str, object], ...]
    parameters: tuple[str, ...] = ()
    description: str | None = None
    defaults: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BotScriptMacro":
        parameters: Iterable[str] = data.get("parameters") or data.get("params") or ()
        defaults = data.get("defaults") or {}
        return cls(
            name=str(data.get("name")),
            steps=tuple(dict(step) if isinstance(step, dict) else {"type": "command", "value": step} for step in data.get("steps", ())),
            parameters=tuple(str(param) for param in parameters),
            description=str(data.get("description")) if data.get("description") else None,
            defaults={str(key): value for key, value in dict(defaults).items()},
        )

    def argument_mapping(self, arguments: object | None) -> dict[str, object]:
        mapping: dict[str, object] = dict(self.defaults)
        if isinstance(arguments, dict):
            mapping.update({str(key): value for key, value in arguments.items()})
        elif isinstance(arguments, (list, tuple)):
            for index, value in enumerate(arguments):
                if index < len(self.parameters):
                    mapping[self.parameters[index]] = value
        elif arguments is not None:
            if self.parameters:
                mapping[self.parameters[0]] = arguments
        return mapping

    def expand(
        self,
        compiler: "ScenarioCompiler",
        arguments: object | None,
        stack: tuple[str, ...],
    ) -> list[dict[str, object]]:
        if self.name in stack:
            raise ValueError(f"Wykryto rekurencyjne wywołanie makra '{self.name}'")
        call_context = dict(compiler.variables)
        call_context.update(self.argument_mapping(arguments))
        expanded: list[dict[str, object]] = []
        for step in self.steps:
            substituted = _replace_placeholders(step, call_context)
            expanded.extend(compiler._compile_step(substituted, stack + (self.name,)))
        return expanded


class ScenarioCompiler:
    """Expand macros and placeholders for scenario steps."""

    def __init__(
        self,
        macros: Mapping[str, BotScriptMacro] | None = None,
        variables: Mapping[str, object] | None = None,
    ) -> None:
        self.macros = dict(macros or {})
        self.variables = dict(variables or {})

    def _normalise_step(self, step: dict | str) -> dict[str, object]:
        if isinstance(step, str):
            return {"type": "command", "value": step}
        if not isinstance(step, dict):
            raise TypeError(f"Nieobsługiwany typ kroku scenariusza: {type(step)!r}")
        return dict(step)

    def _compile_step(self, step: dict | str, stack: tuple[str, ...]) -> list[dict[str, object]]:
        data = self._normalise_step(step)
        step_type = str(data.get("type") or data.get("action") or data.get("macro") or "command")
        if step_type in {"macro", "use_macro"} or "macro" in data:
            name = str(data.get("name")) if data.get("name") else str(data.get("macro"))
            macro = self.macros.get(name)
            if macro is None:
                raise KeyError(f"Nie znaleziono makra scenariusza '{name}'")
            arguments = (
                data.get("arguments")
                or data.get("args")
                or data.get("with")
                or data.get("values")
            )
            return macro.expand(self, arguments, stack)
        if step_type in {"set_variables", "with_variables"}:
            overrides = (
                data.get("values")
                or data.get("variables")
                or data.get("with")
                or data.get("arguments")
                or {}
            )
            merged = dict(self.variables)
            merged.update({str(key): value for key, value in dict(overrides).items()})
            inner_steps = data.get("steps")
            if inner_steps is None:
                raise ValueError("Sekcja set_variables wymaga pola 'steps'")
            inner_compiler = ScenarioCompiler(macros=self.macros, variables=merged)
            compiled: list[dict[str, object]] = []
            for inner_step in inner_steps:
                compiled.extend(inner_compiler._compile_step(inner_step, stack))
            return compiled
        substituted = _replace_placeholders(data, self.variables)
        return [self._normalise_step(substituted)]

    def compile(self, steps: Sequence[dict | str]) -> list[dict[str, object]]:
        compiled: list[dict[str, object]] = []
        for step in steps:
            compiled.extend(self._compile_step(step, ()))
        return compiled


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
    macros: Mapping[str, BotScriptMacro] = field(default_factory=dict)
    variables: Mapping[str, object] = field(default_factory=dict)

    def normalised_steps(self) -> list[ScenarioStep]:
        compiler = ScenarioCompiler(macros=self.macros, variables=self.variables)
        expanded = compiler.compile(self.steps)
        return [ScenarioStep.from_dict(step) for step in expanded]

    def to_bot_script(self) -> BotScript:
        steps = self.normalised_steps()
        commands = tuple(step.to_command() for step in steps)
        actions = tuple(step.to_payload() for step in steps)
        return BotScript(description=self.description, commands=commands, actions=actions)


__all__ = ["ScenarioStep", "BotScenarioSpec", "BotScriptMacro", "ScenarioCompiler"]
