"""Configuration models for generating SA-MP RP gamemodes."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Sequence

from .pawn import escape_pawn_string, indent_lines, sanitize_identifier
from .scenario import BotScenarioSpec


def _parse_colour(value: int | str) -> int:
    if isinstance(value, int):
        return value
    stripped = value.strip()
    if stripped.startswith("0x"):
        return int(stripped, 16)
    if stripped.startswith("#"):
        hex_part = stripped[1:]
        if len(hex_part) == 6:
            return int(hex_part + "FF", 16)
        return int(hex_part, 16)
    return int(stripped)


@dataclass(slots=True)
class TeleportAction:
    """Teleport the player to a given position."""

    x: float
    y: float
    z: float
    interior: int = 0
    world: int = 0

    def to_pawn(self) -> list[str]:
        lines = [f"SetPlayerPos(playerid, {self.x}, {self.y}, {self.z});"]
        if self.interior:
            lines.append(f"SetPlayerInterior(playerid, {self.interior});")
        if self.world:
            lines.append(f"SetPlayerVirtualWorld(playerid, {self.world});")
        return lines


@dataclass(slots=True)
class SpawnPoint:
    """Represents a spawn location for players."""

    x: float
    y: float
    z: float
    angle: float = 0.0
    interior: int = 0
    world: int = 0

    def to_pawn(self) -> str:
        return (
            f"AddPlayerClass(0, {self.x}, {self.y}, {self.z}, {self.angle}, 0, 0, 0, 0, 0, 0);"
        )


@dataclass(slots=True)
class VehicleSpawn:
    """Defines a vehicle spawn point."""

    model: int
    x: float
    y: float
    z: float
    rotation: float
    colour1: int = 0
    colour2: int = 0
    respawn_delay: int = 60

    def to_pawn(self) -> str:
        return (
            "AddStaticVehicleEx("
            f"{self.model}, {self.x}, {self.y}, {self.z}, {self.rotation}, "
            f"{self.colour1}, {self.colour2}, {self.respawn_delay});"
        )


@dataclass(slots=True)
class Faction:
    """Basic faction definition."""

    name: str
    description: str
    colour: int | str

    def __post_init__(self) -> None:
        self.colour = _parse_colour(self.colour)

    @property
    def constant(self) -> str:
        return f"FACTION_{sanitize_identifier(self.name)}"

    def to_pawn_comment(self) -> str:
        return (
            f"// Faction: {self.name} ({self.description}) colour 0x{self.colour:08X}"
        )

    def array_entry(self) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        return (
            f'    {{"{name}", "{description}", 0x{self.colour:08X}}}'
        )


@dataclass(slots=True)
class Command:
    """High level command specification."""

    trigger: str
    responses: Sequence[str] = field(default_factory=list)
    grant_money: int | None = None
    teleport: TeleportAction | None = None
    required_faction: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Command":
        teleport_data = data.get("teleport")
        teleport = TeleportAction(**teleport_data) if teleport_data else None
        return cls(
            trigger=data["trigger"],
            responses=tuple(data.get("responses", [])),
            grant_money=data.get("grant_money"),
            teleport=teleport,
            required_faction=data.get("required_faction"),
        )

    def pawn_lines(self, prefix: str = "if") -> list[str]:
        trigger = escape_pawn_string(self.trigger)
        lines: list[str] = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        for message in self.responses:
            escaped = escape_pawn_string(message)
            lines.append(f'    SendClientMessage(playerid, 0xFFFFFFFF, "{escaped}");')
        if self.grant_money is not None:
            lines.append(f"    GivePlayerMoney(playerid, {self.grant_money});")
        if self.teleport is not None:
            for action_line in self.teleport.to_pawn():
                lines.append(f"    {action_line}")
        lines.append("    return 1;")
        lines.append("}")
        return lines


@dataclass(slots=True)
class Item:
    """Represents an inventory item available on the server."""

    name: str
    description: str
    price: int
    weight: float = 0.0

    def array_entry(self) -> str:
        return (
            "    {"
            f'"{escape_pawn_string(self.name)}", '
            f'"{escape_pawn_string(self.description)}", '
            f"{self.price}, "
            f"{self.weight:.3f}"
            "}"
        )


@dataclass(slots=True)
class EconomySettings:
    """High level economy configuration."""

    base_paycheck: int = 500
    paycheck_interval: int = 3600
    tax_rate: float = 0.05
    default_bank_balance: int = 1000

    def definitions(self) -> str:
        return (
            "enum eEconomyData {\n"
            "    EconomyPaycheck,\n"
            "    EconomyTaxRate,\n"
            "    EconomyInterval,\n"
            "    EconomyDefaultBank\n"
            "};\n"
            "new Float:gEconomy[eEconomyData];"
        )

    def setup_lines(self) -> list[str]:
        return [
            f"gEconomy[EconomyPaycheck] = {self.base_paycheck};",
            f"gEconomy[EconomyInterval] = {self.paycheck_interval};",
            f"gEconomy[EconomyTaxRate] = {self.tax_rate:.4f};",
            f"gEconomy[EconomyDefaultBank] = {self.default_bank_balance};",
        ]


@dataclass(slots=True)
class JobTask:
    """Single step inside a job storyline."""

    description: str
    reward: int
    command_hint: str | None = None

    def to_pawn(self) -> str:
        description = escape_pawn_string(self.description)
        hint = escape_pawn_string(self.command_hint or "")
        return f'    {{"{description}", {self.reward}, "{hint}"}}'


@dataclass(slots=True)
class Job:
    """Basic job definition for the generated gamemode."""

    name: str
    description: str
    salary: int
    join_command: str
    required_faction: str | None = None
    tasks: Sequence[JobTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.join_command.startswith("/"):
            self.join_command = "/" + self.join_command

    @property
    def constant(self) -> str:
        return f"JOB_{sanitize_identifier(self.name)}"

    def array_entry(self) -> str:
        description = escape_pawn_string(self.description)
        name = escape_pawn_string(self.name)
        join = escape_pawn_string(self.join_command)
        return (
            "    {"
            f'"{name}", "{description}", {self.salary}, "{join}", '
            f"{self._required_faction_constant()}"
            "}"
        )

    def _required_faction_constant(self) -> str:
        if not self.required_faction:
            return "INVALID_FACTION"
        return f"FACTION_{sanitize_identifier(self.required_faction)}"

    def tasks_array(self) -> str:
        if not self.tasks:
            return "new gJobTasks_" + self.constant + "[][eJobTask] = {};"
        body = ",\n".join(task.to_pawn() for task in self.tasks)
        return (
            "new gJobTasks_" + self.constant + "[][eJobTask] = {\n" + body + "\n};"
        )


@dataclass(slots=True)
class Pickup:
    """Static pickup spawned on the map."""

    model: int
    type: int
    x: float
    y: float
    z: float
    world: int = 0
    interior: int = 0
    respawn: int = 30

    def to_pawn(self) -> str:
        return (
            "CreatePickup("
            f"{self.model}, {self.type}, {self.x}, {self.y}, {self.z}, {self.world}, {self.respawn});"
        )


@dataclass(slots=True)
class BotScenarioDefinition:
    """Configuration of a bot scenario to be materialised as a BotScript."""

    name: str
    description: str
    steps: Sequence[dict]

    @classmethod
    def from_dict(cls, data: dict) -> "BotScenarioDefinition":
        return cls(
            name=data.get("name", data.get("description", "scenario")),
            description=data.get("description", data.get("name", "Scenario")),
            steps=tuple(data.get("steps", [])),
        )

    def to_spec(self) -> BotScenarioSpec:
        return BotScenarioSpec(name=self.name, description=self.description, steps=self.steps)


@dataclass(slots=True)
class ServerSettings:
    """Settings written into server.cfg."""

    hostname: str = "AutoRP Development Server"
    rcon_password: str = "autorp"
    port: int = 7777
    max_players: int = 50
    language: str = "pl"
    weburl: str = "autorprp.local"
    announce: int = 0
    lanmode: int = 1
    plugins: Sequence[str] = field(default_factory=list)
    filterscripts: Sequence[str] = field(default_factory=list)

    def to_server_cfg(self, gamemode: str) -> str:
        lines = [
            "echo -------- AutoRP generated server.cfg --------",
            f"hostname {self.hostname}",
            f"lanmode {self.lanmode}",
            f"rcon_password {self.rcon_password}",
            f"maxplayers {self.max_players}",
            f"port {self.port}",
            f"language {self.language}",
            f"weburl {self.weburl}",
            f"announce {self.announce}",
            f"gamemode0 {gamemode} 1",
        ]
        if self.filterscripts:
            lines.append("filterscripts " + " ".join(self.filterscripts))
        if self.plugins:
            lines.append("plugins " + " ".join(self.plugins))
        lines.append("echo -------------------------------------------")
        return "\n".join(lines) + "\n"


@dataclass(slots=True)
class WorldSettings:
    """Global world settings applied on OnGameModeInit."""

    time: int = 12
    weather: int = 1
    gravity: float = 0.008
    stunt_bonus: bool = False
    interior_enter_exits: bool = False
    name_tag_draw_distance: float = 20.0
    use_player_ped_anims: bool = True

    def to_pawn(self) -> list[str]:
        lines = [
            f"SetWorldTime({self.time});",
            f"SetWeather({self.weather});",
            f"SetGravity({self.gravity});",
            f"SetNameTagDrawDistance({self.name_tag_draw_distance});",
        ]
        lines.append(f"EnableStuntBonusForAll({1 if self.stunt_bonus else 0});")
        if not self.interior_enter_exits:
            lines.append("DisableInteriorEnterExits();")
        if self.use_player_ped_anims:
            lines.append("UsePlayerPedAnims();")
        return lines


@dataclass(slots=True)
class GamemodeConfig:
    """Global configuration for a generated gamemode."""

    name: str
    description: str
    author: str
    welcome_message: str = "Witamy na serwerze RP!"
    default_faction: str | None = None
    factions: Sequence[Faction] = field(default_factory=list)
    spawn_points: Sequence[SpawnPoint] = field(default_factory=list)
    vehicles: Sequence[VehicleSpawn] = field(default_factory=list)
    commands: Sequence[Command] = field(default_factory=list)
    items: Sequence[Item] = field(default_factory=list)
    jobs: Sequence[Job] = field(default_factory=list)
    pickups: Sequence[Pickup] = field(default_factory=list)
    scenarios: Sequence[BotScenarioDefinition] = field(default_factory=list)
    server_settings: ServerSettings = field(default_factory=ServerSettings)
    world_settings: WorldSettings = field(default_factory=WorldSettings)
    economy: EconomySettings = field(default_factory=EconomySettings)

    @classmethod
    def from_dict(cls, data: dict) -> "GamemodeConfig":
        factions = [Faction(**f) for f in data.get("factions", [])]
        spawn_points = [SpawnPoint(**s) for s in data.get("spawn_points", [])]
        vehicles = [VehicleSpawn(**v) for v in data.get("vehicles", [])]
        commands = [Command.from_dict(c) for c in data.get("commands", [])]
        items = [Item(**item) for item in data.get("items", [])]
        jobs = [
            Job(
                name=j["name"],
                description=j.get("description", j["name"]),
                salary=j.get("salary", 0),
                join_command=j.get("join_command", f"join_{sanitize_identifier(j['name']).lower()}"),
                required_faction=j.get("required_faction"),
                tasks=[JobTask(**task) for task in j.get("tasks", [])],
            )
            for j in data.get("jobs", [])
        ]
        pickups = [Pickup(**p) for p in data.get("pickups", [])]
        scenarios = [BotScenarioDefinition.from_dict(s) for s in data.get("bot_scenarios", [])]
        server_settings = ServerSettings(**data.get("server", {}))
        world_settings = WorldSettings(**data.get("world", {}))
        economy = EconomySettings(**data.get("economy", {}))
        return cls(
            name=data.get("name", "AutoRP"),
            description=data.get(
                "description", "Automatycznie wygenerowany gamemode RP"
            ),
            author=data.get("author", "AutoRP"),
            welcome_message=data.get("welcome_message", "Witamy na serwerze RP!"),
            default_faction=data.get("default_faction"),
            factions=factions,
            spawn_points=spawn_points,
            vehicles=vehicles,
            commands=commands,
            items=items,
            jobs=jobs,
            pickups=pickups,
            scenarios=scenarios,
            server_settings=server_settings,
            world_settings=world_settings,
            economy=economy,
        )

    def ensure_output_directory(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def faction_lookup(self) -> dict[str, Faction]:
        return {f.name: f for f in self.factions}

    def _default_faction_constant(self) -> str:
        if not self.factions:
            return "FACTION_CIVILIAN"
        if self.default_faction:
            faction = self.faction_lookup().get(self.default_faction)
            if faction:
                return faction.constant
        return self.factions[0].constant

    def _faction_enum(self) -> str:
        if not self.factions:
            return "enum eFactionId { FACTION_CIVILIAN };"
        entries = ["FACTION_CIVILIAN"] + [f.constant for f in self.factions]
        formatted = ",\n    ".join(entries)
        return "enum eFactionId {\n    " + formatted + "\n};"

    def _faction_definitions(self) -> str:
        entries = [
            '    {"Cywile", "Domyślna frakcja RP", 0xFFFFFFFF}'
        ] + [f.array_entry() for f in self.factions]
        body = ",\n".join(entries)
        return (
            "enum eFactionData {\n"
            "    FactionName[32],\n"
            "    FactionDescription[128],\n"
            "    FactionColour\n"
            "};\n\n"
            "new gFactions[][eFactionData] = {\n"
            f"{body}\n"
            "};"
        )

    def _faction_setup_lines(self) -> list[str]:
        if not self.factions:
            return ["printf(\"[AutoRP] Brak frakcji do inicjalizacji\");"]
        return [
            "for (new i = 0; i < sizeof(gFactions); i++)",
            "{",
            '    printf("[AutoRP] Zarejestrowano frakcję: %s", gFactions[i][FactionName]);',
            "}",
        ]

    def _world_lines(self) -> list[str]:
        return self.world_settings.to_pawn()

    def _spawn_lines(self) -> list[str]:
        if not self.spawn_points:
            return ["// Domyślne spawny GTA:SA"]
        return [sp.to_pawn() for sp in self.spawn_points]

    def _vehicle_lines(self) -> list[str]:
        if not self.vehicles:
            return ["// Brak zdefiniowanych pojazdów"]
        return [vehicle.to_pawn() for vehicle in self.vehicles]

    def _command_lines(self) -> list[str]:
        lines: list[str] = []
        for index, command in enumerate(self.commands):
            prefix = "if" if index == 0 else "else if"
            command_lines = command.pawn_lines(prefix=prefix)
            if command.required_faction:
                faction = self.faction_lookup().get(command.required_faction)
                if faction:
                    guard = [
                        f"    if (PlayerFaction[playerid] != {faction.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "Brak dostępu do tej komendy.");',
                        "        return 1;",
                        "    }",
                    ]
                    command_lines[2:2] = guard
            lines.extend(command_lines)

        job_lines = self._job_command_lines("if" if not lines else "else if")
        lines.extend(job_lines)
        if not lines:
            return ["// Brak zdefiniowanych komend", "return 0;"]
        lines.append("return 0;")
        return lines

    def _job_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.jobs:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        for job in self.jobs:
            trigger = escape_pawn_string(job.join_command)
            block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
            faction_constant = job._required_faction_constant()
            if faction_constant != "INVALID_FACTION":
                block.extend(
                    [
                        f"    if (PlayerFaction[playerid] != {faction_constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "To stanowisko jest zarezerwowane dla frakcji.");',
                        "        return 1;",
                        "    }",
                    ]
                )
            block.extend(
                [
                    f"    PlayerJob[playerid] = {job.constant};",
                    f'    SendClientMessage(playerid, 0x33AA33FF, "Dołączyłeś do pracy: {escape_pawn_string(job.name)}");',
                    f"    SetTimerEx(\"HandleJobPaycheck\", floatround(gEconomy[EconomyInterval]), false, \"dd\", playerid, {job.salary});",
                    "    return 1;",
                    "}",
                ]
            )
            prefix = "else if"
            lines.extend(block)
        return lines

    def _item_definitions(self) -> str:
        if not self.items:
            return "new gItems[][eItemData] = {};"
        body = ",\n".join(item.array_entry() for item in self.items)
        return (
            "new gItems[][eItemData] = {\n"
            f"{body}\n"
            "};"
        )

    def _job_definitions(self) -> str:
        if not self.jobs:
            return "new gJobs[][eJobData] = {};"
        body = ",\n".join(job.array_entry() for job in self.jobs)
        return (
            "new gJobs[][eJobData] = {\n"
            f"{body}\n"
            "};"
        )

    def _job_task_definitions(self) -> list[str]:
        lines: list[str] = []
        for job in self.jobs:
            lines.append(job.tasks_array())
        return lines or ["// Brak zdefiniowanych zadań"]

    def _job_enum(self) -> str:
        if not self.jobs:
            return "enum eJobId { JOB_NONE };"
        entries = ["JOB_NONE"] + [job.constant for job in self.jobs]
        formatted = ",\n    ".join(entries)
        return "enum eJobId {\n    " + formatted + "\n};"

    def _pickup_lines(self) -> list[str]:
        if not self.pickups:
            return ["// Brak pickupów"]
        return [pickup.to_pawn() for pickup in self.pickups]

    def bot_scripts(self) -> list["BotScript"]:
        from .tester import BotScript

        scripts: list[BotScript] = []
        for scenario in self.scenarios:
            spec = scenario.to_spec()
            scripts.append(spec.to_bot_script())
        return scripts

    def write_bot_scripts(self, directory: Path) -> list[Path]:
        directory.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for script in self.bot_scripts():
            filename = sanitize_identifier(script.description or "scenario") or "scenario"
            target = directory / f"{filename}.json"
            target.write_text(script.to_json(), encoding="utf-8")
            paths.append(target)
        return paths

    def server_cfg_content(self) -> str:
        return self.server_settings.to_server_cfg(self.name)

    def metadata_json(self) -> str:
        payload = {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "welcome_message": self.welcome_message,
            "factions": [f.name for f in self.factions],
            "commands": [cmd.trigger for cmd in self.commands],
            "jobs": [job.name for job in self.jobs],
            "items": [item.name for item in self.items],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def pawn_context(self) -> dict:
        return {
            "metadata_banner": (
                f"/*\n    AutoRP generated gamemode\n    Name: {self.name}\n"
                f"    Author: {self.author}\n    Description: {self.description}\n*/"
            ),
            "name": escape_pawn_string(self.name),
            "description": escape_pawn_string(self.description),
            "author": escape_pawn_string(self.author),
            "welcome_message": escape_pawn_string(self.welcome_message),
            "default_faction_constant": self._default_faction_constant(),
            "faction_enum": self._faction_enum(),
            "faction_definitions": self._faction_definitions(),
            "server_commands": indent_lines(
                [
                    f'SendRconCommand("hostname {escape_pawn_string(self.server_settings.hostname)}");',
                    f'SendRconCommand("password {escape_pawn_string(self.server_settings.rcon_password)}");',
                ],
                level=1,
            ),
            "world_setup": indent_lines(self._world_lines(), level=1),
            "faction_setup": indent_lines(self._faction_setup_lines(), level=1),
            "spawn_points": indent_lines(self._spawn_lines(), level=1),
            "vehicle_spawns": indent_lines(self._vehicle_lines(), level=1),
            "command_handlers": indent_lines(self._command_lines(), level=1),
            "economy_definitions": self.economy.definitions(),
            "economy_setup": indent_lines(self.economy.setup_lines(), level=1),
            "item_definitions": self._item_definitions(),
            "job_definitions": self._job_definitions(),
            "job_enum": self._job_enum(),
            "job_task_definitions": "\n".join(self._job_task_definitions()),
            "pickup_setup": indent_lines(self._pickup_lines(), level=1),
        }


__all__ = [
    "GamemodeConfig",
    "Faction",
    "SpawnPoint",
    "VehicleSpawn",
    "Command",
    "ServerSettings",
    "WorldSettings",
    "TeleportAction",
    "Item",
    "EconomySettings",
    "Job",
    "JobTask",
    "Pickup",
    "BotScenarioDefinition",
]
