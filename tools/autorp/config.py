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
class PropertyPoint:
    """Entrance or exit point for a property."""

    x: float
    y: float
    z: float
    interior: int = 0
    world: int = 0
    angle: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "PropertyPoint":
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 0.0),
            interior=data.get("interior", 0),
            world=data.get("world", 0),
            angle=data.get("angle", 0.0),
        )

    def format_coords(self) -> tuple[str, str, str]:
        return (f"{self.x}", f"{self.y}", f"{self.z}")

    def format_angle(self) -> str:
        return f"{self.angle}"


@dataclass(slots=True)
class Property:
    """Describes a buyable property with a world entrance."""

    name: str
    description: str
    price: int
    entrance: PropertyPoint
    interior: PropertyPoint
    required_faction: str | None = None
    pickup_model: int = 1273
    pickup_type: int = 1
    pickup_respawn: int = 30
    purchase_command: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Property":
        entrance = PropertyPoint.from_dict(data.get("entrance", {}))
        interior = PropertyPoint.from_dict(data.get("interior", {}))
        return cls(
            name=data["name"],
            description=data.get("description", data["name"]),
            price=data.get("price", 0),
            entrance=entrance,
            interior=interior,
            required_faction=data.get("required_faction"),
            pickup_model=data.get("pickup_model", 1273),
            pickup_type=data.get("pickup_type", 1),
            pickup_respawn=data.get("pickup_respawn", 30),
            purchase_command=data.get("purchase_command"),
        )

    def __post_init__(self) -> None:
        if self.purchase_command and not self.purchase_command.startswith("/"):
            self.purchase_command = "/" + self.purchase_command

    @property
    def constant(self) -> str:
        return f"PROPERTY_{sanitize_identifier(self.name)}"

    def _faction_constant(self) -> str:
        if not self.required_faction:
            return "INVALID_FACTION"
        return f"FACTION_{sanitize_identifier(self.required_faction)}"

    def command_trigger(self) -> str:
        if self.purchase_command:
            return self.purchase_command
        base = sanitize_identifier(self.name).lower()
        return f"/kup_{base}"

    def array_entry(self) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        entrance_x, entrance_y, entrance_z = self.entrance.format_coords()
        interior_x, interior_y, interior_z = self.interior.format_coords()
        return (
            "    {"
            f'"{name}", "{description}", '
            f"{entrance_x}, {entrance_y}, {entrance_z}, {self.entrance.format_angle()}, "
            f"{self.entrance.interior}, {self.entrance.world}, "
            f"{interior_x}, {interior_y}, {interior_z}, {self.interior.format_angle()}, "
            f"{self.interior.interior}, {self.interior.world}, {self.price}, {self._faction_constant()}"
            "}"
        )

    def pickup_setup_line(self) -> str:
        return (
            f"    gPropertyPickups[{self.constant}] = CreatePickup("
            f"{self.pickup_model}, {self.pickup_type}, {self.entrance.x}, {self.entrance.y}, {self.entrance.z}, {self.entrance.world}, {self.pickup_respawn});"
        )

    def command_block(self, prefix: str, factions: dict[str, Faction]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        lines = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        faction_guard = factions.get(self.required_faction) if self.required_faction else None
        if faction_guard:
            lines.extend(
                [
                    f"    if (PlayerFaction[playerid] != {faction_guard.constant})",
                    "    {",
                    '        SendClientMessage(playerid, 0xAA3333FF, "Tylko odpowiednia frakcja może kupić tę nieruchomość.");',
                    "        return 1;",
                    "    }",
                ]
            )
        lines.extend(
            [
                "    new info[160];",
                f"    format(info, sizeof(info), \"Oferta: %s - cena: %d$\", gProperties[{self.constant}][PropertyName], gProperties[{self.constant}][PropertyPrice]);",
                "    SendClientMessage(playerid, 0x55FF55FF, info);",
                f"    SendClientMessage(playerid, 0xFFFFFFFF, gProperties[{self.constant}][PropertyDescription]);",
                f"    return HandlePropertyPurchase(playerid, {self.constant});",
                "}",
            ]
        )
        return lines


@dataclass(slots=True)
class Npc:
    """Non-playable character spawned for flavour and automation."""

    name: str
    skin: int
    x: float
    y: float
    z: float
    angle: float = 0.0
    dialogue: Sequence[str] = field(default_factory=list)
    command: str | None = None
    faction: str | None = None

    def __post_init__(self) -> None:
        if self.command and not self.command.startswith("/"):
            self.command = "/" + self.command

    @property
    def constant(self) -> str:
        return f"NPC_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        if self.command:
            return self.command
        return f"/rozmowa_{sanitize_identifier(self.name).lower()}"

    def spawn_lines(self) -> list[str]:
        safe_name = escape_pawn_string(self.name)
        return [
            f"    gNpcActors[{self.constant}] = CreateActor({self.skin}, {self.x}, {self.y}, {self.z}, {self.angle});",
            f'    printf("[AutoRP] NPC %s zainicjalizowany", "{safe_name}");',
        ]

    def dialogue_lines(self) -> list[str]:
        lines: list[str] = []
        colour = "0xFFE4B5FF"
        prefix = escape_pawn_string(self.name)
        for message in self.dialogue:
            escaped = escape_pawn_string(message)
            lines.append(
                f'    SendClientMessage(playerid, {colour}, "[{prefix}] {escaped}");'
            )
        if not lines:
            lines.append(
                f'    SendClientMessage(playerid, {colour}, "[{prefix}] Miłego dnia!");'
            )
        return lines

    def command_block(self, prefix: str, factions: dict[str, Faction]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        if self.faction:
            faction = factions.get(self.faction)
            if faction:
                block.extend(
                    [
                        f"    if (PlayerFaction[playerid] != {faction.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "Tylko odpowiednia frakcja może porozmawiać z tym NPC.");',
                        "        return 1;",
                        "    }",
                    ]
                )
        block.extend(self.dialogue_lines())
        block.append("    return 1;")
        block.append("}")
        return block


@dataclass(slots=True)
class ScheduledEvent:
    """Recurring scripted event executed on a timer."""

    name: str
    interval_ms: int
    announce: Sequence[str] = field(default_factory=list)
    grant_money: int | None = None
    target_faction: str | None = None
    rcon_command: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledEvent":
        announce = data.get("announce")
        if isinstance(announce, str):
            announce = [announce]
        return cls(
            name=data["name"],
            interval_ms=data.get("interval_ms", data.get("interval", 60000)),
            announce=tuple(announce or ()),
            grant_money=data.get("grant_money"),
            target_faction=data.get("target_faction"),
            rcon_command=data.get("rcon_command"),
        )

    @property
    def constant(self) -> str:
        return f"EVENT_{sanitize_identifier(self.name)}"

    def forward(self) -> str:
        return f"forward {self.handler_name()}();"

    def handler_name(self) -> str:
        return f"HandleScheduledEvent_{sanitize_identifier(self.name)}"

    def timer_setup_line(self) -> str:
        return f'    SetTimer("{self.handler_name()}", {self.interval_ms}, true);'

    def handler_block(self, factions: dict[str, Faction]) -> str:
        lines: list[str] = [f"public {self.handler_name()}()", "{"]
        for message in self.announce:
            escaped = escape_pawn_string(message)
            lines.append(
                f'    SendClientMessageToAll(0x33AA33FF, "[Event] {escaped}");'
            )
        if self.grant_money is not None:
            if self.target_faction:
                faction = factions.get(self.target_faction)
                if faction:
                    lines.extend(
                        [
                            "    for (new playerid = 0; playerid < MAX_PLAYERS; playerid++)",
                            "    {",
                            "        if(!IsPlayerConnected(playerid))",
                            "        {",
                            "            continue;",
                            "        }",
                            f"        if (PlayerFaction[playerid] != {faction.constant})",
                            "        {",
                            "            continue;",
                            "        }",
                            f"        GivePlayerMoney(playerid, {self.grant_money});",
                            "    }",
                        ]
                    )
            else:
                lines.extend(
                    [
                        "    for (new playerid = 0; playerid < MAX_PLAYERS; playerid++)",
                        "    {",
                        "        if(!IsPlayerConnected(playerid))",
                        "        {",
                        "            continue;",
                        "        }",
                        f"        GivePlayerMoney(playerid, {self.grant_money});",
                        "    }",
                    ]
                )
        if self.rcon_command:
            command = escape_pawn_string(self.rcon_command)
            lines.append(f'    SendRconCommand("{command}");')
        lines.append("    return 1;")
        lines.append("}")
        return "\n".join(lines)


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
    properties: Sequence[Property] = field(default_factory=list)
    npcs: Sequence[Npc] = field(default_factory=list)
    events: Sequence[ScheduledEvent] = field(default_factory=list)
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
        properties = [Property.from_dict(p) for p in data.get("properties", [])]
        npcs = [Npc(**npc) for npc in data.get("npcs", [])]
        events = [ScheduledEvent.from_dict(e) for e in data.get("events", [])]
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
            properties=properties,
            npcs=npcs,
            events=events,
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

        property_lines = self._property_command_lines("if" if not lines else "else if")
        lines.extend(property_lines)

        npc_lines = self._npc_command_lines("if" if not lines else "else if")
        lines.extend(npc_lines)
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

    def _property_enum(self) -> str:
        if not self.properties:
            return "enum ePropertyId { PROPERTY_COUNT = 0 };"
        entries = [prop.constant for prop in self.properties] + ["PROPERTY_COUNT"]
        formatted = ",\n    ".join(entries)
        return "enum ePropertyId {\n    " + formatted + "\n};"

    def _property_definitions(self) -> str:
        if not self.properties:
            return "// Brak zdefiniowanych nieruchomości"
        body = ",\n".join(prop.array_entry() for prop in self.properties)
        return (
            "enum ePropertyData {\n"
            "    PropertyName[48],\n"
            "    PropertyDescription[128],\n"
            "    Float:PropertyEntranceX,\n"
            "    Float:PropertyEntranceY,\n"
            "    Float:PropertyEntranceZ,\n"
            "    Float:PropertyEntranceAngle,\n"
            "    PropertyEntranceInterior,\n"
            "    PropertyEntranceWorld,\n"
            "    Float:PropertyExitX,\n"
            "    Float:PropertyExitY,\n"
            "    Float:PropertyExitZ,\n"
            "    Float:PropertyExitAngle,\n"
            "    PropertyExitInterior,\n"
            "    PropertyExitWorld,\n"
            "    PropertyPrice,\n"
            "    PropertyFaction\n"
            "};\n\n"
            "new gProperties[][ePropertyData] = {\n"
            f"{body}\n"
            "};"
        )

    def _property_pickup_array(self) -> str:
        if not self.properties:
            return "// Brak nieruchomości - brak tablic pickupów"
        return "new gPropertyPickups[PROPERTY_COUNT];"

    def _property_setup_lines(self) -> list[str]:
        if not self.properties:
            return ["printf(\"[AutoRP] Brak nieruchomości do inicjalizacji\");"]
        lines: list[str] = []
        for prop in self.properties:
            lines.append(prop.pickup_setup_line())
            lines.append(
                f'    printf("[AutoRP] Zarejestrowano nieruchomość: %s", gProperties[{prop.constant}][PropertyName]);'
            )
        return lines

    def _property_pickup_handlers(self) -> list[str]:
        if not self.properties:
            return ["    return 1; // Brak nieruchomości"]
        return [
            "    for (new i = 0; i < PROPERTY_COUNT; i++)",
            "    {",
            "        if (gPropertyPickups[i] == pickupid)",
            "        {",
            "            new info[160];",
            "            format(info, sizeof(info), \"Nieruchomość: %s - cena: %d$\", gProperties[i][PropertyName], gProperties[i][PropertyPrice]);",
            "            SendClientMessage(playerid, 0x55FF55FF, info);",
            "            SendClientMessage(playerid, 0xFFFFFFFF, gProperties[i][PropertyDescription]);",
            "            return 1;",
            "        }",
            "    }",
            "    return 1;",
        ]

    def _property_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.properties:
            return []
        lines: list[str] = []
        prefix = initial_prefix
        factions = self.faction_lookup()
        for prop in self.properties:
            block = prop.command_block(prefix, factions)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _npc_enum(self) -> str:
        if not self.npcs:
            return "enum eNpcId { NPC_COUNT = 0 };"
        entries = [npc.constant for npc in self.npcs] + ["NPC_COUNT"]
        formatted = ",\n    ".join(entries)
        return "enum eNpcId {\n    " + formatted + "\n};"

    def _npc_actor_array(self) -> str:
        if not self.npcs:
            return "// Brak NPC do utworzenia"
        return "new gNpcActors[NPC_COUNT];"

    def _npc_setup_lines(self) -> list[str]:
        if not self.npcs:
            return ["printf(\"[AutoRP] Brak NPC do inicjalizacji\");"]
        lines: list[str] = []
        for npc in self.npcs:
            lines.extend(npc.spawn_lines())
        return lines

    def _npc_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.npcs:
            return []
        lines: list[str] = []
        prefix = initial_prefix
        factions = self.faction_lookup()
        for npc in self.npcs:
            block = npc.command_block(prefix, factions)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _event_forwards(self) -> str:
        if not self.events:
            return "// Brak zaplanowanych eventów"
        return "\n".join(event.forward() for event in self.events)

    def _event_setup_lines(self) -> list[str]:
        if not self.events:
            return ["printf(\"[AutoRP] Brak eventów do zarejestrowania\");"]
        return [event.timer_setup_line() for event in self.events]

    def _event_handlers(self) -> str:
        if not self.events:
            return "// Brak obsługi zdarzeń"
        factions = self.faction_lookup()
        return "\n\n".join(event.handler_block(factions) for event in self.events)

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
            "properties": [prop.name for prop in self.properties],
            "npcs": [npc.name for npc in self.npcs],
            "events": [event.name for event in self.events],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def pawn_context(self) -> dict:
        property_pickup_handlers = "\n".join(self._property_pickup_handlers())
        if property_pickup_handlers:
            property_pickup_handlers += "\n"
        event_handlers = self._event_handlers()
        if event_handlers:
            event_handlers += "\n"
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
            "property_enum": self._property_enum(),
            "property_definitions": self._property_definitions(),
            "property_pickup_array": self._property_pickup_array(),
            "property_setup": indent_lines(self._property_setup_lines(), level=1),
            "property_pickup_handlers": property_pickup_handlers,
            "npc_enum": self._npc_enum(),
            "npc_actor_array": self._npc_actor_array(),
            "npc_setup": indent_lines(self._npc_setup_lines(), level=1),
            "event_forwards": self._event_forwards(),
            "event_setup": indent_lines(self._event_setup_lines(), level=1),
            "event_handlers": event_handlers,
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
    "Property",
    "PropertyPoint",
    "Npc",
    "ScheduledEvent",
    "BotScenarioDefinition",
]
