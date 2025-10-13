"""Configuration models for generating SA-MP RP gamemodes."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Sequence

from .pawn import escape_pawn_string, indent_lines, sanitize_identifier
from .scenario import BotScenarioSpec
from .tester import (
    BotRunContext,
    ClientLogExpectation,
    ClientLogExportRequest,
)


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
class QuestStep:
    """Single step inside a quest chain."""

    description: str
    hint: str | None = None
    teleport: TeleportAction | None = None
    reward_money: int = 0
    give_item: str | None = None
    take_item: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "QuestStep":
        teleport = data.get("teleport")
        return cls(
            description=data.get("description", ""),
            hint=data.get("hint"),
            teleport=TeleportAction(**teleport) if teleport else None,
            reward_money=data.get("reward_money", 0),
            give_item=data.get("give_item"),
            take_item=data.get("take_item"),
        )

    def array_entry(self) -> str:
        description = escape_pawn_string(self.description)
        hint = escape_pawn_string(self.hint or "")
        has_teleport = 1 if self.teleport else 0
        if self.teleport:
            x, y, z = self.teleport.x, self.teleport.y, self.teleport.z
            interior = self.teleport.interior
            world = self.teleport.world
        else:
            x = y = z = 0.0
            interior = 0
            world = 0
        reward = self.reward_money or 0
        give_item = escape_pawn_string(self.give_item or "")
        take_item = escape_pawn_string(self.take_item or "")
        return (
            "    {"
            f'"{description}", "{hint}", {has_teleport}, '
            f"{x}, {y}, {z}, {interior}, {world}, {reward}, "
            f'"{give_item}", "{take_item}"'
            "}"
        )


@dataclass(slots=True)
class Quest:
    """Narrative quest consisting of a series of steps."""

    name: str
    description: str
    steps: Sequence[QuestStep]
    start_command: str | None = None
    required_faction: str | None = None
    reward_money: int = 0
    reward_item: str | None = None
    completion_message: str | None = None

    def __post_init__(self) -> None:
        if self.start_command and not self.start_command.startswith("/"):
            self.start_command = "/" + self.start_command

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
        steps = [QuestStep.from_dict(step) for step in data.get("steps", [])]
        command = data.get("start_command")
        if not command:
            command = "/quest_" + sanitize_identifier(data.get("name", "quest")).lower()
        return cls(
            name=data.get("name", "Quest"),
            description=data.get("description", ""),
            steps=tuple(steps),
            start_command=command,
            required_faction=data.get("required_faction"),
            reward_money=data.get("reward_money", 0),
            reward_item=data.get("reward_item"),
            completion_message=data.get("completion_message"),
        )

    @property
    def constant(self) -> str:
        return f"QUEST_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        return self.start_command or ("/quest_" + sanitize_identifier(self.name).lower())

    def array_entry(self, factions: dict[str, Faction], step_start: int) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        command = escape_pawn_string(self.command_trigger())
        faction_constant = "INVALID_FACTION"
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                faction_constant = faction.constant
        reward_item = escape_pawn_string(self.reward_item or "")
        completion = escape_pawn_string(self.completion_message or "")
        return (
            "    {"
            f'"{name}", "{description}", "{command}", {faction_constant}, '
            f"{self.reward_money}, "
            f'"{reward_item}", "{completion}", {step_start}, {len(self.steps)}'
            "}"
        )

    def step_entries(self) -> list[str]:
        return [step.array_entry() for step in self.steps]

    def offset_entry(self, step_start: int) -> str:
        return f"    {{{step_start}, {len(self.steps)}}}"

    def command_block(self, prefix: str, factions: dict[str, Faction]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                block.extend(
                    [
                        f"    if (PlayerFaction[playerid] != {faction.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "Ta misja wymaga odpowiedniej frakcji.");',
                        "        return 1;",
                        "    }",
                    ]
                )
        block.extend(
            [
                f"    StartQuest(playerid, {self.constant});",
                "    return 1;",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class Business:
    """Interactive business with pickup information and purchase flow."""

    name: str
    type: str
    product: str
    price: int
    stock: int = 0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    interior: int = 0
    world: int = 0
    pickup_model: int = 1274
    pickup_type: int = 1
    pickup_respawn: int = 30
    command: str | None = None
    required_faction: str | None = None
    required_job: str | None = None

    def __post_init__(self) -> None:
        if self.command and not self.command.startswith("/"):
            self.command = "/" + self.command

    @classmethod
    def from_dict(cls, data: dict) -> "Business":
        return cls(
            name=data.get("name", "Biznes"),
            type=data.get("type", "Sklep"),
            product=data.get("product", "Towar"),
            price=data.get("price", 0),
            stock=data.get("stock", 0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 0.0),
            interior=data.get("interior", 0),
            world=data.get("world", 0),
            pickup_model=data.get("pickup_model", 1274),
            pickup_type=data.get("pickup_type", 1),
            pickup_respawn=data.get("pickup_respawn", 30),
            command=data.get("command"),
            required_faction=data.get("required_faction"),
            required_job=data.get("required_job"),
        )

    @property
    def constant(self) -> str:
        return f"BUSINESS_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        if self.command:
            return self.command
        return f"/biznes_{sanitize_identifier(self.name).lower()}"

    def array_entry(self, factions: dict[str, Faction], jobs: dict[str, "Job"]) -> str:
        name = escape_pawn_string(self.name)
        btype = escape_pawn_string(self.type)
        product = escape_pawn_string(self.product)
        faction_constant = "INVALID_FACTION"
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                faction_constant = faction.constant
        job_constant = "JOB_NONE"
        if self.required_job:
            job = jobs.get(self.required_job)
            if job:
                job_constant = job.constant
        command = escape_pawn_string(self.command_trigger())
        return (
            "    {"
            f'"{name}", "{btype}", "{product}", {self.price}, {self.stock}, '
            f"{self.x}, {self.y}, {self.z}, {self.interior}, {self.world}, {self.pickup_model}, "
            f"{self.pickup_type}, {self.pickup_respawn}, {faction_constant}, {job_constant}, "
            f'"{command}"'
            "}"
        )

    def setup_lines(self) -> list[str]:
        return [
            f"    gBusinessPickups[{self.constant}] = CreatePickup({self.pickup_model}, {self.pickup_type}, {self.x}, {self.y}, {self.z}, {self.world}, {self.pickup_respawn});",
            f'    printf("[AutoRP] Biznes aktywny: %s", gBusinesses[{self.constant}][BusinessName]);',
        ]

    def command_block(self, prefix: str, factions: dict[str, Faction], jobs: dict[str, "Job"]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                block.extend(
                    [
                        f"    if (PlayerFaction[playerid] != {faction.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "To przedsiębiorstwo należy do innej frakcji.");',
                        "        return 1;",
                        "    }",
                    ]
                )
        if self.required_job:
            job = jobs.get(self.required_job)
            if job:
                block.extend(
                    [
                        f"    if (PlayerJob[playerid] != {job.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "Najpierw dołącz do wymaganej pracy.");',
                        "        return 1;",
                        "    }",
                    ]
                )
        block.extend(
            [
                f"    HandleBusinessPurchase(playerid, {self.constant});",
                "    return 1;",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class CraftingIngredient:
    """Single ingredient required for a crafting recipe."""

    item: str
    quantity: int = 1

    @classmethod
    def from_dict(cls, data: dict | str) -> "CraftingIngredient":
        if isinstance(data, str):
            return cls(item=data, quantity=1)
        return cls(item=data.get("item", ""), quantity=data.get("quantity", 1))

    def summary(self) -> str:
        return f"{self.quantity}x {self.item}"


@dataclass(slots=True)
class CraftingRecipe:
    """Definition of a crafting recipe accessible via command."""

    name: str
    description: str
    inputs: Sequence[CraftingIngredient]
    output_item: str
    output_quantity: int = 1
    command: str | None = None
    required_job: str | None = None

    def __post_init__(self) -> None:
        if self.command and not self.command.startswith("/"):
            self.command = "/" + self.command

    @classmethod
    def from_dict(cls, data: dict) -> "CraftingRecipe":
        ingredients = [
            CraftingIngredient.from_dict(ing)
            for ing in data.get("inputs", [])
        ]
        command = data.get("command")
        if not command:
            command = "/craft_" + sanitize_identifier(data.get("name", "recipe")).lower()
        return cls(
            name=data.get("name", "Przepis"),
            description=data.get("description", ""),
            inputs=tuple(ingredients),
            output_item=data.get("output_item", ""),
            output_quantity=data.get("output_quantity", 1),
            command=command,
            required_job=data.get("required_job"),
        )

    def command_trigger(self) -> str:
        return self.command or ("/craft_" + sanitize_identifier(self.name).lower())

    def array_entry(self, jobs: dict[str, "Job"]) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        command = escape_pawn_string(self.command_trigger())
        output_item = escape_pawn_string(self.output_item)
        job_constant = "JOB_NONE"
        if self.required_job:
            job = jobs.get(self.required_job)
            if job:
                job_constant = job.constant
        summary = escape_pawn_string(
            ", ".join(ingredient.summary() for ingredient in self.inputs)
        )
        return (
            "    {"
            f'"{name}", "{description}", "{command}", "{summary}", '
            f'"{output_item}", {self.output_quantity}, {job_constant}'
            "}"
        )

    def command_block(self, prefix: str, jobs: dict[str, "Job"]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        if self.required_job:
            job = jobs.get(self.required_job)
            if job:
                block.extend(
                    [
                        f"    if (PlayerJob[playerid] != {job.constant})",
                        "    {",
                        '        SendClientMessage(playerid, 0xAA3333FF, "Wymagana jest odpowiednia praca do wytwarzania.");',
                        "        return 1;",
                        "    }",
                    ]
                )
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        output_item = escape_pawn_string(self.output_item)
        block.append(
            f'    SendClientMessage(playerid, 0x33AA33FF, "Przepis: {name} -> {self.output_quantity}x {output_item}");'
        )
        if description:
            block.append(
                f'    SendClientMessage(playerid, 0xFFFFFFFF, "{description}");'
            )
        for ingredient in self.inputs:
            summary = escape_pawn_string(ingredient.summary())
            block.append(
                f'    SendClientMessage(playerid, 0xCCCCCCFF, "- {summary}");'
            )
        block.extend(
            [
                '    SendClientMessage(playerid, 0x8888FFFF, "System magazynu i składników wymaga implementacji serwerowej.");',
                "    return 1;",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class Achievement:
    """Simple achievement unlocked via command or scripted event."""

    name: str
    description: str
    reward_money: int = 0
    announce_global: bool = False
    command: str | None = None

    def __post_init__(self) -> None:
        if self.command and not self.command.startswith("/"):
            self.command = "/" + self.command

    @classmethod
    def from_dict(cls, data: dict) -> "Achievement":
        command = data.get("command")
        if not command:
            command = "/achievement_" + sanitize_identifier(data.get("name", "achievement")).lower()
        return cls(
            name=data.get("name", "Osiągnięcie"),
            description=data.get("description", ""),
            reward_money=data.get("reward_money", 0),
            announce_global=bool(data.get("announce_global", False)),
            command=command,
        )

    @property
    def constant(self) -> str:
        return f"ACHIEVEMENT_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        return self.command or ("/achievement_" + sanitize_identifier(self.name).lower())

    def array_entry(self) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        announce = 1 if self.announce_global else 0
        return (
            "    {"
            f'"{name}", "{description}", {self.reward_money}, {announce}'
            "}"
        )

    def command_block(self, index: int, prefix: str) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                f"    if (PlayerAchievements[playerid][{index}])",
                "    {",
                '        SendClientMessage(playerid, 0xAAAAAAFF, "To osiągnięcie zostało już odebrane.");',
                "        return 1;",
                "    }",
                f"    PlayerAchievements[playerid][{index}] = true;",
                "    new msg[144];",
                f'    format(msg, sizeof(msg), "Zdobywasz osiągnięcie: %s", gAchievements[{index}][AchievementName]);',
                "    SendClientMessage(playerid, 0xFFD700FF, msg);",
                f"    if (gAchievements[{index}][AchievementRewardMoney] > 0)",
                "    {",
                f"        GivePlayerMoney(playerid, gAchievements[{index}][AchievementRewardMoney]);",
                "    }",
                "    if (gAchievements[{index}][AchievementAnnounceGlobal])",
                "    {",
                "        new pname[MAX_PLAYER_NAME];",
                "        GetPlayerName(playerid, pname, sizeof(pname));",
                "        new announce[188];",
                f'        format(announce, sizeof(announce), "[AutoRP] %s zdobył osiągnięcie %s!", pname, gAchievements[{index}][AchievementName]);',
                "        SendClientMessageToAll(0xFFD700FF, announce);",
                "    }",
                "    return 1;",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class SkillLevel:
    """Configuration for a single skill level."""

    xp: int
    reward_message: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SkillLevel":
        return cls(
            xp=data.get("xp", data.get("experience", 0)),
            reward_message=data.get("reward_message") or data.get("message"),
        )


@dataclass(slots=True)
class Skill:
    """Skill with progressive XP tiers."""

    name: str
    description: str
    progress_command: str | None = None
    levels: Sequence[SkillLevel] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.progress_command:
            if not self.progress_command.startswith("/"):
                self.progress_command = "/" + self.progress_command
        else:
            self.progress_command = "/skill_" + sanitize_identifier(self.name).lower()

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        levels = [SkillLevel.from_dict(level) for level in data.get("levels", [])]
        if not levels:
            levels = [SkillLevel(xp=100)]
        return cls(
            name=data.get("name", "Umiejętność"),
            description=data.get("description", ""),
            progress_command=data.get("command"),
            levels=tuple(levels),
        )

    @property
    def constant(self) -> str:
        return f"SKILL_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        assert self.progress_command is not None
        return self.progress_command

    def level_count(self) -> int:
        return len(self.levels)

    def array_entry(self) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        command = escape_pawn_string(self.command_trigger())
        return f'    {{"{name}", "{description}", "{command}", {self.level_count()}}}'

    def xp_row(self, max_levels: int) -> str:
        values = [str(level.xp) for level in self.levels]
        values.extend("0" for _ in range(max_levels - len(values)))
        return "    {" + ", ".join(values) + "}"

    def reward_row(self, max_levels: int) -> str:
        messages = [escape_pawn_string(level.reward_message or "") for level in self.levels]
        messages.extend("" for _ in range(max_levels - len(messages)))
        formatted = ",\n        ".join(f'"{msg}"' for msg in messages)
        return "    {\n        " + formatted + "\n    }"

    def command_block(self, index: int, prefix: str) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                "    new buffer[200];",
                f'    format(buffer, sizeof(buffer), "Umiejętność: %s (poziom %d)", gSkills[{index}][SkillName], PlayerSkillLevel[playerid][{index}]);',
                "    SendClientMessage(playerid, 0x55AAFFFF, buffer);",
                f'    format(buffer, sizeof(buffer), "Postęp: %d/%d XP", PlayerSkillXp[playerid][{index}], gSkillLevelXp[{index}][PlayerSkillLevel[playerid][{index}]]);',
                "    SendClientMessage(playerid, 0xFFFFFFFF, buffer);",
                "    SendClientMessage(playerid, 0xCCCCFFFF, gSkills[{index}][SkillDescription]);",
                "    return 1;",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class SkillTraining:
    """Definition of a training command that awards skill XP."""

    name: str
    skill: str
    command: str
    xp_gain: int
    description: str = ""
    cooldown: int = 60
    success_message: str | None = None

    def __post_init__(self) -> None:
        if not self.command.startswith("/"):
            self.command = "/" + self.command

    @classmethod
    def from_dict(cls, data: dict) -> "SkillTraining":
        return cls(
            name=data.get("name", "Trening"),
            skill=data.get("skill", ""),
            command=data.get("command", "/trening"),
            xp_gain=data.get("xp_gain", data.get("xp", 25)),
            description=data.get("description", ""),
            cooldown=data.get("cooldown", 60),
            success_message=data.get("success_message"),
        )

    @property
    def constant(self) -> str:
        return f"SKILL_TRAINING_{sanitize_identifier(self.name)}"

    def array_entry(self, skills: dict[str, "Skill"]) -> str:
        skill = skills.get(self.skill)
        skill_constant = skill.constant if skill else "SKILL_NONE"
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        command = escape_pawn_string(self.command)
        success = escape_pawn_string(self.success_message or "")
        return (
            "    {"
            f'"{name}", "{description}", "{command}", {skill_constant}, {self.xp_gain}, {self.cooldown}, "{success}"'
            "}"
        )

    def command_block(self, index: int, prefix: str) -> list[str]:
        trigger = escape_pawn_string(self.command)
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                f"    return HandleSkillTraining(playerid, {index});",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class Territory:
    """Captureable territory with periodic income."""

    name: str
    description: str
    x: float
    y: float
    z: float
    radius: float
    owner_faction: str | None = None
    income: int = 0
    capture_time: int = 60
    reward_money: int = 0
    info_command: str | None = None
    capture_command: str | None = None
    broadcast_message: str | None = None

    def __post_init__(self) -> None:
        if self.info_command:
            if not self.info_command.startswith("/"):
                self.info_command = "/" + self.info_command
        else:
            self.info_command = "/teren_" + sanitize_identifier(self.name).lower()
        if self.capture_command:
            if not self.capture_command.startswith("/"):
                self.capture_command = "/" + self.capture_command
        else:
            self.capture_command = "/przejmij_" + sanitize_identifier(self.name).lower()

    @classmethod
    def from_dict(cls, data: dict) -> "Territory":
        return cls(
            name=data.get("name", "Teren"),
            description=data.get("description", ""),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 0.0),
            radius=data.get("radius", 5.0),
            owner_faction=data.get("owner_faction"),
            income=data.get("income", 0),
            capture_time=data.get("capture_time", 60),
            reward_money=data.get("reward_money", 0),
            info_command=data.get("info_command"),
            capture_command=data.get("capture_command"),
            broadcast_message=data.get("broadcast_message"),
        )

    @property
    def constant(self) -> str:
        return f"TERRITORY_{sanitize_identifier(self.name)}"

    def info_trigger(self) -> str:
        assert self.info_command is not None
        return self.info_command

    def capture_trigger(self) -> str:
        assert self.capture_command is not None
        return self.capture_command

    def array_entry(self, factions: dict[str, "Faction"]) -> str:
        faction_constant = "INVALID_FACTION"
        if self.owner_faction:
            faction = factions.get(self.owner_faction)
            if faction:
                faction_constant = faction.constant
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        info_command = escape_pawn_string(self.info_trigger())
        capture_command = escape_pawn_string(self.capture_trigger())
        broadcast = escape_pawn_string(self.broadcast_message or "")
        return (
            "    {"
            f'"{name}", "{description}", {self.x}, {self.y}, {self.z}, {self.radius}, '
            f"{faction_constant}, {self.income}, {self.capture_time}, {self.reward_money}, "
            f'"{info_command}", "{capture_command}", "{broadcast}"'
            "}"
        )

    def info_command_block(self, index: int, prefix: str) -> list[str]:
        trigger = escape_pawn_string(self.info_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                "    new buffer[200];",
                f'    format(buffer, sizeof(buffer), "Teren %s - kontrola frakcji %d", gTerritories[{index}][TerritoryName], TerritoryOwners[{index}]);',
                "    SendClientMessage(playerid, 0x77CC77FF, buffer);",
                "    SendClientMessage(playerid, 0xFFFFFFFF, gTerritories[{index}][TerritoryDescription]);",
                f'    format(buffer, sizeof(buffer), "Dochód: %d$ co cykl", gTerritories[{index}][TerritoryIncome]);',
                "    SendClientMessage(playerid, 0x77CC77FF, buffer);",
                "    return 1;",
                "}",
            ]
        )
        return block

    def capture_command_block(self, index: int, prefix: str) -> list[str]:
        trigger = escape_pawn_string(self.capture_trigger())
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                f"    return StartTerritoryCapture(playerid, {index});",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class LawViolation:
    """Represents a law violation that can be assigned to a player."""

    code: str
    name: str
    description: str
    severity: int = 1
    fine: int = 0
    jail_minutes: int = 0
    reputation_penalty: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "LawViolation":
        return cls(
            code=data.get("code", "UNK"),
            name=data.get("name", data.get("title", "Wykroczenie")),
            description=data.get("description", ""),
            severity=data.get("severity", data.get("level", 1)),
            fine=data.get("fine", data.get("penalty", 0)),
            jail_minutes=data.get("jail_minutes", data.get("jail", 0)),
            reputation_penalty=data.get("reputation_penalty", data.get("reputation", 0)),
        )

    @property
    def constant(self) -> str:
        return f"LAW_{sanitize_identifier(self.code)}"

    def array_entry(self) -> str:
        name = escape_pawn_string(self.name)
        description = escape_pawn_string(self.description)
        code = escape_pawn_string(self.code)
        return (
            "    {"
            f'"{code}", "{name}", "{description}", {self.severity}, {self.fine}, {self.jail_minutes}, {self.reputation_penalty}'
            "}"
        )


@dataclass(slots=True)
class PatrolPoint:
    """Single point of a patrol route."""

    x: float
    y: float
    z: float
    wait_seconds: int = 5

    @classmethod
    def from_dict(cls, data: dict) -> "PatrolPoint":
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 5.0),
            wait_seconds=data.get("wait_seconds", data.get("wait", 5)),
        )

    def array_entry(self) -> str:
        return f"    {{{self.x}, {self.y}, {self.z}, {self.wait_seconds}}}"


@dataclass(slots=True)
class PatrolRoute:
    """Predefined patrol run for law enforcement factions."""

    name: str
    faction: str
    points: Sequence[PatrolPoint] = field(default_factory=list)
    loop: bool = True
    command: str | None = None
    radio_message: str | None = None

    def __post_init__(self) -> None:
        if self.command:
            if not self.command.startswith("/"):
                self.command = "/" + self.command
        else:
            self.command = "/patrol_" + sanitize_identifier(self.name).lower()
        if self.radio_message is None:
            self.radio_message = f"Rozpoczynasz patrol: {self.name}"

    @classmethod
    def from_dict(cls, data: dict) -> "PatrolRoute":
        points = [PatrolPoint.from_dict(point) for point in data.get("points", [])]
        return cls(
            name=data.get("name", "Patrol"),
            faction=data.get("faction", data.get("required_faction", "")),
            points=points,
            loop=data.get("loop", True),
            command=data.get("command"),
            radio_message=data.get("radio_message"),
        )

    @property
    def constant(self) -> str:
        return f"PATROL_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        assert self.command is not None
        return self.command

    def array_entry(self, factions: dict[str, "Faction"], point_start: int) -> str:
        faction = factions.get(self.faction)
        faction_constant = faction.constant if faction else "INVALID_FACTION"
        name = escape_pawn_string(self.name)
        command = escape_pawn_string(self.command_trigger())
        radio = escape_pawn_string(self.radio_message or "")
        return (
            "    {"
            f'"{name}", {faction_constant}, {point_start}, {len(self.points)}, {1 if self.loop else 0}, "{command}", "{radio}"'
            "}"
        )

    def command_block(self, index: int, prefix: str, factions: dict[str, "Faction"]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        faction = factions.get(self.faction)
        faction_constant = faction.constant if faction else "INVALID_FACTION"
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                f"    return StartPatrol(playerid, {index}, {faction_constant});",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class HeistStage:
    """Single stage of a cooperative heist."""

    description: str
    success_message: str | None = None
    failure_message: str | None = None
    time_limit: int = 60

    @classmethod
    def from_dict(cls, data: dict) -> "HeistStage":
        return cls(
            description=data.get("description", ""),
            success_message=data.get("success_message"),
            failure_message=data.get("failure_message"),
            time_limit=data.get("time_limit", data.get("duration", 60)),
        )

    def array_entry(self) -> str:
        description = escape_pawn_string(self.description)
        success = escape_pawn_string(self.success_message or "")
        failure = escape_pawn_string(self.failure_message or "")
        return (
            "    {"
            f'"{description}", {self.time_limit}, "{success}", "{failure}"'
            "}"
        )


@dataclass(slots=True)
class Heist:
    """Complex crime scenario with multi-stage progression."""

    name: str
    location: str
    cooldown_minutes: int
    required_players: int = 1
    required_faction: str | None = None
    required_items: Sequence[str] = field(default_factory=list)
    reward_money: int = 0
    reward_item: str | None = None
    reward_reputation: int = 0
    start_command: str | None = None
    announcement: str | None = None
    stages: Sequence[HeistStage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.start_command:
            if not self.start_command.startswith("/"):
                self.start_command = "/" + self.start_command
        else:
            self.start_command = "/heist_" + sanitize_identifier(self.name).lower()
        if self.announcement is None:
            self.announcement = f"Rozpoczyna się napad: {self.name}"

    @classmethod
    def from_dict(cls, data: dict) -> "Heist":
        stages = [HeistStage.from_dict(stage) for stage in data.get("stages", [])]
        return cls(
            name=data.get("name", "Heist"),
            location=data.get("location", ""),
            cooldown_minutes=data.get("cooldown_minutes", data.get("cooldown", 30)),
            required_players=data.get("required_players", data.get("players", 1)),
            required_faction=data.get("required_faction"),
            required_items=data.get("required_items", data.get("items", [])),
            reward_money=data.get("reward_money", data.get("reward", 0)),
            reward_item=data.get("reward_item"),
            reward_reputation=data.get("reward_reputation", data.get("reputation", 0)),
            start_command=data.get("start_command"),
            announcement=data.get("announcement"),
            stages=stages,
        )

    @property
    def constant(self) -> str:
        return f"HEIST_{sanitize_identifier(self.name)}"

    def command_trigger(self) -> str:
        assert self.start_command is not None
        return self.start_command

    def array_entry(self, factions: dict[str, "Faction"], stage_start: int) -> str:
        faction_constant = "INVALID_FACTION"
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                faction_constant = faction.constant
        name = escape_pawn_string(self.name)
        location = escape_pawn_string(self.location)
        items = escape_pawn_string(
            ",".join(self.required_items) if self.required_items else ""
        )
        announcement = escape_pawn_string(self.announcement or "")
        reward_item = escape_pawn_string(self.reward_item or "")
        return (
            "    {"
            f'"{name}", "{location}", {self.cooldown_minutes}, {self.required_players}, '
            f"{stage_start}, {len(self.stages)}, {self.reward_money}, "
            f'"{reward_item}", {self.reward_reputation}, "{items}", {faction_constant}, "{announcement}"'
            "}"
        )

    def command_block(self, index: int, prefix: str, factions: dict[str, "Faction"]) -> list[str]:
        trigger = escape_pawn_string(self.command_trigger())
        faction_constant = "INVALID_FACTION"
        if self.required_faction:
            faction = factions.get(self.required_faction)
            if faction:
                faction_constant = faction.constant
        block = [f"{prefix}(!strcmp(cmdtext, \"{trigger}\", true))", "{"]
        block.extend(
            [
                f"    return StartHeist(playerid, {index}, {faction_constant});",
                "}",
            ]
        )
        return block


@dataclass(slots=True)
class WeatherStage:
    """Single stage of a dynamic weather cycle."""

    hour: int
    weather: int
    duration_minutes: int
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "WeatherStage":
        return cls(
            hour=data.get("hour", 12),
            weather=data.get("weather", data.get("weather_id", 1)),
            duration_minutes=data.get("duration_minutes", data.get("duration", 15)),
            description=data.get("description"),
        )

    def array_entry(self) -> str:
        description = escape_pawn_string(self.description or "")
        return (
            "    {"
            f"{self.hour}, {self.weather}, {self.duration_minutes}, "
            f'"{description}"'
            "}"
        )


@dataclass(slots=True)
class WeatherCycle:
    """Collection of weather stages that will rotate automatically."""

    stages: Sequence[WeatherStage]

    @classmethod
    def from_dict(cls, data: dict | Sequence[dict]) -> "WeatherCycle":
        if isinstance(data, dict) and "stages" in data:
            stage_data = data.get("stages", [])
        else:
            stage_data = data
        stages = [WeatherStage.from_dict(stage) for stage in stage_data or []]
        return cls(stages=tuple(stages))

    def array_definition(self) -> str:
        if not self.stages:
            return "new gWeatherStages[][eWeatherStageData] = {};"
        body = ",\n".join(stage.array_entry() for stage in self.stages)
        return (
            "new gWeatherStages[][eWeatherStageData] = {\n"
            f"{body}\n"
            "};"
        )

    def setup_lines(self) -> list[str]:
        if not self.stages:
            return ["printf(\"[AutoRP] Brak zdefiniowanego cyklu pogody\");"]
        return ["ApplyWeatherStage(0);"]


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
class BotClientLogDefinition:
    """Definition describing a client-side log file."""

    name: str
    path: str
    encoding: str = "utf-8"

    @classmethod
    def from_dict(cls, data: dict) -> "BotClientLogDefinition":
        return cls(
            name=str(data.get("name", "log")),
            path=str(data.get("path")),
            encoding=str(data.get("encoding", "utf-8")),
        )


@dataclass(slots=True)
class BotClientDefinition:
    """Definition describing how to instantiate a bot client."""

    name: str
    type: str = "dummy"
    command_file: str | None = None
    command_separator: str | None = None
    gta_directory: str | None = None
    launcher: str | None = None
    wine_binary: str | None = None
    dry_run: bool = False
    connect_delay: float = 0.0
    reset_commands_on_connect: bool = True
    environment: dict[str, str] = field(default_factory=dict)
    focus_window: bool = False
    window_title: str | None = None
    xdotool_binary: str | None = None
    chatlog: str | None = None
    chatlog_encoding: str | None = None
    logs: tuple[BotClientLogDefinition, ...] = ()
    setup_actions: tuple[dict[str, object], ...] = ()
    teardown_actions: tuple[dict[str, object], ...] = ()
    options: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "BotClientDefinition":
        logs = tuple(
            BotClientLogDefinition.from_dict(entry)
            for entry in data.get("logs", [])
            if entry
        )
        setup_actions = tuple(dict(action) for action in data.get("setup_actions", []))
        if not setup_actions:
            setup_actions = tuple(dict(action) for action in data.get("setup", []))
        teardown_actions = tuple(dict(action) for action in data.get("teardown_actions", []))
        if not teardown_actions:
            teardown_actions = tuple(dict(action) for action in data.get("teardown", []))
        return cls(
            name=str(data.get("name")),
            type=str(data.get("type", "dummy")),
            command_file=data.get("command_file"),
            command_separator=data.get("command_separator"),
            gta_directory=data.get("gta_dir") or data.get("gta_directory"),
            launcher=data.get("launcher"),
            wine_binary=data.get("wine_binary"),
            dry_run=bool(data.get("dry_run", False)),
            connect_delay=float(data.get("connect_delay", 0.0)),
            reset_commands_on_connect=bool(data.get("reset_commands_on_connect", True)),
            environment=dict(data.get("environment", {})),
            focus_window=bool(data.get("focus_window", False)),
            window_title=data.get("window_title"),
            xdotool_binary=data.get("xdotool_binary"),
            chatlog=data.get("chatlog"),
            chatlog_encoding=data.get("chatlog_encoding"),
            logs=logs,
            setup_actions=setup_actions,
            teardown_actions=teardown_actions,
            options=dict(data.get("options", {})),
        )


@dataclass(slots=True)
class BotClientLogExpectationDefinition:
    """Expectation configuration for client-side log assertions."""

    client: str
    phrase: str
    log: str = "chatlog"
    timeout: float | None = None
    poll_interval: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "BotClientLogExpectationDefinition":
        return cls(
            client=str(data.get("client", data.get("name"))),
            phrase=str(data.get("phrase", data.get("text", ""))),
            log=str(data.get("log", data.get("source", "chatlog"))),
            timeout=(
                float(data["timeout"]) if data.get("timeout") is not None else None
            ),
            poll_interval=(
                float(data["poll_interval"]) if data.get("poll_interval") is not None else None
            ),
        )

    def to_expectation(self) -> ClientLogExpectation:
        return ClientLogExpectation(
            client_name=self.client,
            phrase=self.phrase,
            log_name=self.log,
            timeout=self.timeout,
            poll_interval=self.poll_interval if self.poll_interval is not None else 0.5,
        )


@dataclass(slots=True)
class BotClientLogExportDefinition:
    """Definition describing a log file that should be exported after a run."""

    client: str
    log: str = "chatlog"
    target: str | None = None
    include_full: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "BotClientLogExportDefinition":
        return cls(
            client=str(data.get("client", data.get("name"))),
            log=str(data.get("log", data.get("source", "chatlog"))),
            target=(str(data.get("target")) if data.get("target") is not None else None),
            include_full=bool(data.get("include_full", data.get("full", False))),
        )

    def to_request(self) -> ClientLogExportRequest:
        return ClientLogExportRequest(
            client_name=self.client,
            log_name=self.log,
            target_path=Path(self.target) if self.target is not None else None,
            include_full_log=self.include_full,
        )


@dataclass(slots=True)
class BotRunDefinition:
    """Definition of a suite run connecting scripts and clients."""

    scenario: str
    clients: tuple[str, ...] = ()
    expect_server_logs: tuple[str, ...] = ()
    log_timeout: float = 15.0
    iterations: int = 1
    wait_after: float = 0.0
    expect_client_logs: tuple["BotClientLogExpectationDefinition", ...] = ()
    wait_before: float = 0.0
    record_playback_dir: str | None = None
    collect_server_log: bool = False
    server_log_export: str | None = None
    export_client_logs: tuple[BotClientLogExportDefinition, ...] = ()
    tags: tuple[str, ...] = ()
    retries: int = 0
    grace_period: float = 0.0
    fail_fast: bool = False
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "BotRunDefinition":
        scenario_name = data.get("scenario") or data.get("script") or data.get("name")
        if scenario_name is None:
            raise ValueError("Bot run definition wymaga pola 'scenario'")
        clients = tuple(str(name) for name in data.get("clients", []))
        expect = tuple(str(entry) for entry in data.get("expect_server_logs", []))
        client_log_expectations = tuple(
            BotClientLogExpectationDefinition.from_dict(entry)
            for entry in data.get("expect_client_logs", [])
        )
        client_log_exports = tuple(
            BotClientLogExportDefinition.from_dict(entry)
            for entry in data.get("export_client_logs", [])
        )
        tags = tuple(str(tag) for tag in data.get("tags", []))
        return cls(
            scenario=str(scenario_name),
            clients=clients,
            expect_server_logs=expect,
            log_timeout=float(data.get("log_timeout", 15.0)),
            iterations=int(data.get("iterations", 1)),
            wait_after=float(data.get("wait_after", 0.0)),
            expect_client_logs=client_log_expectations,
            wait_before=float(data.get("wait_before", 0.0)),
            record_playback_dir=(
                str(data.get("record_playback_dir"))
                if data.get("record_playback_dir") is not None
                else None
            ),
            collect_server_log=bool(data.get("collect_server_log", False)),
            server_log_export=(
                str(data.get("server_log_export"))
                if data.get("server_log_export") is not None
                else None
            ),
            export_client_logs=client_log_exports,
            tags=tags,
            retries=int(data.get("retries", data.get("max_retries", 0))),
            grace_period=float(data.get("grace_period", data.get("retry_delay", 0.0))),
            fail_fast=bool(data.get("fail_fast", False)),
            enabled=bool(data.get("enabled", data.get("active", True))),
        )


@dataclass(slots=True)
class BotAutomationPlan:
    """Plan describing clients and their orchestrated runs."""

    clients: tuple[BotClientDefinition, ...]
    runs: tuple[BotRunDefinition, ...]

    def contexts(self, scenarios: Sequence[BotScenarioDefinition]) -> list[BotRunContext]:
        scenario_lookup = {scenario.name: scenario for scenario in scenarios}
        contexts: list[BotRunContext] = []
        for run in self.runs:
            scenario = scenario_lookup.get(run.scenario)
            if scenario is None:
                continue
            script = scenario.to_spec().to_bot_script()
            contexts.append(
                BotRunContext(
                    script=script,
                    client_names=run.clients,
                    expect_server_logs=run.expect_server_logs,
                    log_timeout=run.log_timeout,
                    iterations=run.iterations,
                    wait_after=run.wait_after,
                    client_log_expectations=tuple(
                        expectation.to_expectation()
                        for expectation in run.expect_client_logs
                    ),
                    wait_before=run.wait_before,
                    record_playback_dir=(
                        Path(run.record_playback_dir)
                        if run.record_playback_dir is not None
                        else None
                    ),
                    capture_server_log=run.collect_server_log,
                    server_log_export=(
                        Path(run.server_log_export)
                        if run.server_log_export is not None
                        else None
                    ),
                    client_log_exports=tuple(
                        export.to_request() for export in run.export_client_logs
                    ),
                    max_retries=max(0, run.retries),
                    grace_period=max(0.0, run.grace_period),
                    fail_fast=run.fail_fast,
                    tags=run.tags,
                    enabled=run.enabled,
                )
            )
        return contexts

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
    bot_clients: Sequence[BotClientDefinition] = field(default_factory=list)
    bot_runs: Sequence[BotRunDefinition] = field(default_factory=list)
    properties: Sequence[Property] = field(default_factory=list)
    npcs: Sequence[Npc] = field(default_factory=list)
    events: Sequence[ScheduledEvent] = field(default_factory=list)
    quests: Sequence[Quest] = field(default_factory=list)
    businesses: Sequence[Business] = field(default_factory=list)
    crafting_recipes: Sequence[CraftingRecipe] = field(default_factory=list)
    achievements: Sequence[Achievement] = field(default_factory=list)
    skills: Sequence[Skill] = field(default_factory=list)
    skill_trainings: Sequence[SkillTraining] = field(default_factory=list)
    territories: Sequence[Territory] = field(default_factory=list)
    law_violations: Sequence[LawViolation] = field(default_factory=list)
    patrol_routes: Sequence[PatrolRoute] = field(default_factory=list)
    heists: Sequence[Heist] = field(default_factory=list)
    patrol_stop_command: str = "/stop_patrol"
    weather_cycle: WeatherCycle | None = None
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
        quests = [Quest.from_dict(q) for q in data.get("quests", [])]
        businesses = [Business.from_dict(b) for b in data.get("businesses", [])]
        crafting_recipes = [
            CraftingRecipe.from_dict(recipe)
            for recipe in data.get("crafting", [])
        ]
        achievements = [
            Achievement.from_dict(achievement)
            for achievement in data.get("achievements", [])
        ]
        skills = [Skill.from_dict(skill) for skill in data.get("skills", [])]
        trainings_data = data.get("skill_trainings") or data.get("trainings", [])
        skill_trainings = [
            SkillTraining.from_dict(training)
            for training in trainings_data
        ]
        territories = [Territory.from_dict(t) for t in data.get("territories", [])]
        law_data = data.get("law", {})
        law_violations = [
            LawViolation.from_dict(violation)
            for violation in law_data.get("violations", [])
        ]
        patrol_routes = [
            PatrolRoute.from_dict(route)
            for route in law_data.get("patrol_routes", [])
        ]
        heists = [Heist.from_dict(heist) for heist in data.get("heists", [])]
        patrol_stop_command = law_data.get("stop_patrol_command", "/stop_patrol")
        if patrol_stop_command and not patrol_stop_command.startswith("/"):
            patrol_stop_command = "/" + patrol_stop_command
        weather_cycle_data = data.get("weather_cycle")
        weather_cycle = (
            WeatherCycle.from_dict(weather_cycle_data)
            if weather_cycle_data
            else None
        )
        scenarios = [BotScenarioDefinition.from_dict(s) for s in data.get("bot_scenarios", [])]
        automation_data = data.get("bot_automation", {})
        bot_clients = [
            BotClientDefinition.from_dict(entry)
            for entry in automation_data.get("clients", [])
        ]
        bot_runs = [
            BotRunDefinition.from_dict(entry)
            for entry in automation_data.get("runs", automation_data.get("suite", []))
        ]
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
            quests=quests,
            businesses=businesses,
            crafting_recipes=crafting_recipes,
            achievements=achievements,
            skills=skills,
            skill_trainings=skill_trainings,
            territories=territories,
            law_violations=law_violations,
            patrol_routes=patrol_routes,
            heists=heists,
            patrol_stop_command=patrol_stop_command,
            weather_cycle=weather_cycle,
            scenarios=scenarios,
            bot_clients=bot_clients,
            bot_runs=bot_runs,
            server_settings=server_settings,
            world_settings=world_settings,
            economy=economy,
        )

    def ensure_output_directory(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def faction_lookup(self) -> dict[str, Faction]:
        return {f.name: f for f in self.factions}

    def job_lookup(self) -> dict[str, Job]:
        return {job.name: job for job in self.jobs}

    def skill_lookup(self) -> dict[str, Skill]:
        return {skill.name: skill for skill in self.skills}

    def scenario_lookup(self) -> dict[str, BotScenarioDefinition]:
        return {scenario.name: scenario for scenario in self.scenarios}

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

        quest_lines = self._quest_command_lines("if" if not lines else "else if")
        lines.extend(quest_lines)

        job_lines = self._job_command_lines("if" if not lines else "else if")
        lines.extend(job_lines)

        crafting_lines = self._crafting_command_lines("if" if not lines else "else if")
        lines.extend(crafting_lines)

        property_lines = self._property_command_lines("if" if not lines else "else if")
        lines.extend(property_lines)

        business_lines = self._business_command_lines("if" if not lines else "else if")
        lines.extend(business_lines)

        npc_lines = self._npc_command_lines("if" if not lines else "else if")
        lines.extend(npc_lines)

        achievement_lines = self._achievement_command_lines("if" if not lines else "else if")
        lines.extend(achievement_lines)

        skill_lines = self._skill_command_lines("if" if not lines else "else if")
        lines.extend(skill_lines)

        training_lines = self._skill_training_command_lines("if" if not lines else "else if")
        lines.extend(training_lines)

        territory_lines = self._territory_command_lines("if" if not lines else "else if")
        lines.extend(territory_lines)

        heist_lines = self._heist_command_lines("if" if not lines else "else if")
        lines.extend(heist_lines)

        patrol_lines = self._patrol_command_lines("if" if not lines else "else if")
        lines.extend(patrol_lines)

        law_lines = self._law_command_lines("if" if not lines else "else if")
        lines.extend(law_lines)
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
            return ["    return 0; // Brak nieruchomości"]
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
            "    return 0;",
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

    def _quest_enum(self) -> str:
        if not self.quests:
            return "enum eQuestId {\n    QUEST_NONE = -1,\n    QUEST_COUNT = 0\n};"
        entries = ["QUEST_NONE = -1"] + [quest.constant for quest in self.quests] + ["QUEST_COUNT"]
        formatted = ",\n    ".join(entries)
        return "enum eQuestId {\n    " + formatted + "\n};"

    def _quest_definitions(self) -> str:
        factions = self.faction_lookup()
        lines = [
            "enum eQuestData {",
            "    QuestName[48],",
            "    QuestDescription[144],",
            "    QuestCommand[32],",
            "    QuestRequiredFaction,",
            "    QuestRewardMoney,",
            "    QuestRewardItem[32],",
            "    QuestCompletionMessage[96],",
            "    QuestStepStart,",
            "    QuestStepCount",
            "};",
        ]
        entries: list[str] = []
        step_start = 0
        for quest in self.quests:
            entries.append(quest.array_entry(factions, step_start))
            step_start += len(quest.steps)
        body = ",\n".join(entries) if entries else ""
        array_lines = [
            "new gQuests[][eQuestData] = {",
            body,
            "};" if entries else "};",
        ]
        if not entries:
            array_lines = ["new gQuests[][eQuestData] = {};"]
        return "\n".join(lines + array_lines)

    def _quest_step_definitions(self) -> str:
        lines = [
            "enum eQuestStepData {",
            "    QuestStepDescription[128],",
            "    QuestStepHint[64],",
            "    QuestStepHasTeleport,",
            "    Float:QuestStepX,",
            "    Float:QuestStepY,",
            "    Float:QuestStepZ,",
            "    QuestStepInterior,",
            "    QuestStepWorld,",
            "    QuestStepRewardMoney,",
            "    QuestStepGiveItem[32],",
            "    QuestStepTakeItem[32]",
            "};",
        ]
        entries = [step for quest in self.quests for step in quest.step_entries()]
        if not entries:
            array_lines = ["new gQuestSteps[][eQuestStepData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gQuestSteps[][eQuestStepData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _quest_step_offsets(self) -> str:
        if not self.quests:
            return "new gQuestStepOffsets[][2] = {};"
        offsets: list[str] = []
        step_start = 0
        for quest in self.quests:
            offsets.append(quest.offset_entry(step_start))
            step_start += len(quest.steps)
        body = ",\n".join(offsets)
        return "new gQuestStepOffsets[][2] = {\n" + body + "\n};"

    def _quest_setup_lines(self) -> list[str]:
        if not self.quests:
            return ["printf(\"[AutoRP] Brak questów do inicjalizacji\");"]
        return [
            "printf(\"[AutoRP] Dostępnych questów: %d\", sizeof(gQuests));",
        ]

    def _quest_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.quests:
            return []
        factions = self.faction_lookup()
        lines: list[str] = []
        prefix = initial_prefix
        for quest in self.quests:
            block = quest.command_block(prefix, factions)
            lines.extend(block)
            prefix = "else if"
        progress_trigger = escape_pawn_string("/questpostep")
        lines.extend(
            [
                f"{prefix}(!strcmp(cmdtext, \"{progress_trigger}\", true))",
                "{",
                "    if (PlayerQuest[playerid] == QUEST_NONE)",
                "    {",
                '        SendClientMessage(playerid, 0xAAAAAAFF, "Nie masz aktywnego questa.");',
                "        return 1;",
                "    }",
                "    ShowQuestProgress(playerid, PlayerQuest[playerid]);",
                "    return 1;",
                "}",
            ]
        )
        prefix = "else if"
        complete_trigger = escape_pawn_string("/questzakoncz")
        lines.extend(
            [
                f"{prefix}(!strcmp(cmdtext, \"{complete_trigger}\", true))",
                "{",
                "    if (PlayerQuest[playerid] == QUEST_NONE)",
                "    {",
                '        SendClientMessage(playerid, 0xAAAAAAFF, "Nie masz aktywnego questa do zakończenia.");',
                "        return 1;",
                "    }",
                "    CompleteQuest(playerid, PlayerQuest[playerid]);",
                "    return 1;",
                "}",
            ]
        )
        return lines

    def _business_enum(self) -> str:
        if not self.businesses:
            return "enum eBusinessId {\n    BUSINESS_COUNT = 0\n};"
        entries = [biz.constant for biz in self.businesses] + ["BUSINESS_COUNT"]
        formatted = ",\n    ".join(entries)
        return "enum eBusinessId {\n    " + formatted + "\n};"

    def _business_definitions(self) -> str:
        lines = [
            "enum eBusinessData {",
            "    BusinessName[48],",
            "    BusinessType[32],",
            "    BusinessProduct[32],",
            "    BusinessPrice,",
            "    BusinessStock,",
            "    Float:BusinessX,",
            "    Float:BusinessY,",
            "    Float:BusinessZ,",
            "    BusinessInterior,",
            "    BusinessWorld,",
            "    BusinessPickupModel,",
            "    BusinessPickupType,",
            "    BusinessPickupRespawn,",
            "    BusinessRequiredFaction,",
            "    BusinessRequiredJob,",
            "    BusinessCommand[32]",
            "};",
        ]
        entries = [
            business.array_entry(self.faction_lookup(), self.job_lookup())
            for business in self.businesses
        ]
        if not entries:
            array_lines = ["new gBusinesses[][eBusinessData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gBusinesses[][eBusinessData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _business_pickup_array(self) -> str:
        if not self.businesses:
            return "// Brak biznesów - brak pickupów"
        return "new gBusinessPickups[sizeof(gBusinesses)];"

    def _business_setup_lines(self) -> list[str]:
        if not self.businesses:
            return ["printf(\"[AutoRP] Brak biznesów do inicjalizacji\");"]
        lines: list[str] = []
        for business in self.businesses:
            lines.extend(business.setup_lines())
        return lines

    def _business_pickup_function_lines(self) -> list[str]:
        if not self.businesses:
            return ["    return 0;"]
        return [
            "    for (new i = 0; i < BUSINESS_COUNT; i++)",
            "    {",
            "        if (gBusinessPickups[i] == pickupid)",
            "        {",
            "            new info[160];",
            "            format(info, sizeof(info), \"Biznes: %s - produkt: %s (%d$)\", gBusinesses[i][BusinessName], gBusinesses[i][BusinessProduct], gBusinesses[i][BusinessPrice]);",
            "            SendClientMessage(playerid, 0x55C1FFFF, info);",
            "            return 1;",
            "        }",
            "    }",
            "    return 0;",
        ]

    def _business_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.businesses:
            return []
        factions = self.faction_lookup()
        jobs = self.job_lookup()
        lines: list[str] = []
        prefix = initial_prefix
        for business in self.businesses:
            block = business.command_block(prefix, factions, jobs)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _crafting_definitions(self) -> str:
        lines = [
            "enum eCraftingData {",
            "    CraftingName[48],",
            "    CraftingDescription[128],",
            "    CraftingCommand[32],",
            "    CraftingInputs[96],",
            "    CraftingOutput[32],",
            "    CraftingOutputCount,",
            "    CraftingRequiredJob",
            "};",
        ]
        entries = [
            recipe.array_entry(self.job_lookup()) for recipe in self.crafting_recipes
        ]
        if not entries:
            array_lines = ["new gCraftingRecipes[][eCraftingData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gCraftingRecipes[][eCraftingData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _crafting_setup_lines(self) -> list[str]:
        if not self.crafting_recipes:
            return ["printf(\"[AutoRP] Brak przepisów rzemieślniczych\");"]
        return [
            "printf(\"[AutoRP] Ładowanie przepisów: %d\", sizeof(gCraftingRecipes));",
        ]

    def _crafting_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.crafting_recipes:
            return []
        jobs = self.job_lookup()
        lines: list[str] = []
        prefix = initial_prefix
        for recipe in self.crafting_recipes:
            block = recipe.command_block(prefix, jobs)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _achievement_enum(self) -> str:
        if not self.achievements:
            return "enum eAchievementId {\n    ACHIEVEMENT_COUNT = 0\n};"
        entries = [ach.constant for ach in self.achievements] + ["ACHIEVEMENT_COUNT"]
        formatted = ",\n    ".join(entries)
        return "enum eAchievementId {\n    " + formatted + "\n};"

    def _achievement_definitions(self) -> str:
        lines = [
            "enum eAchievementData {",
            "    AchievementName[48],",
            "    AchievementDescription[128],",
            "    AchievementRewardMoney,",
            "    AchievementAnnounceGlobal",
            "};",
        ]
        entries = [achievement.array_entry() for achievement in self.achievements]
        if not entries:
            array_lines = ["new gAchievements[][eAchievementData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gAchievements[][eAchievementData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _achievement_setup_lines(self) -> list[str]:
        if not self.achievements:
            return ["printf(\"[AutoRP] Brak osiągnięć do inicjalizacji\");"]
        return [
            "printf(\"[AutoRP] Zarejestrowano osiągnięcia: %d\", sizeof(gAchievements));",
        ]

    def _achievement_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.achievements:
            return []
        lines: list[str] = []
        prefix = initial_prefix
        for index, achievement in enumerate(self.achievements):
            block = achievement.command_block(index, prefix)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _max_skill_levels(self) -> int:
        return max((skill.level_count() for skill in self.skills), default=0)

    def _skill_enum(self) -> str:
        entries = ["SKILL_NONE = -1"] + [skill.constant for skill in self.skills]
        entries.append("SKILL_COUNT")
        formatted = ",\n    ".join(entries)
        return "enum eSkillId {\n    " + formatted + "\n};"

    def _skill_data_enum(self) -> str:
        return "".join(
            [
                "enum eSkillData {\n",
                "    SkillName[48],\n",
                "    SkillDescription[144],\n",
                "    SkillCommand[32],\n",
                "    SkillLevelCount\n",
                "};",
            ]
        )

    def _skill_definitions(self) -> str:
        if not self.skills:
            return "// Brak zdefiniowanych umiejętności"
        entries = ",\n".join(skill.array_entry() for skill in self.skills)
        return "new gSkills[][eSkillData] = {\n" + entries + "\n};"

    def _skill_level_requirements(self) -> str:
        if not self.skills:
            return "// Brak progów doświadczenia dla umiejętności"
        max_levels = self._max_skill_levels()
        rows = ",\n".join(skill.xp_row(max_levels) for skill in self.skills)
        return (
            "new gSkillLevelXp[SKILL_COUNT][SKILL_MAX_LEVELS] = {\n"
            + rows
            + "\n};"
        )

    def _skill_reward_messages(self) -> str:
        if not self.skills:
            return "// Brak komunikatów nagród umiejętności"
        max_levels = self._max_skill_levels()
        rows = ",\n".join(skill.reward_row(max_levels) for skill in self.skills)
        return (
            "new gSkillLevelMessages[SKILL_COUNT][SKILL_MAX_LEVELS][96] = {\n"
            + rows
            + "\n};"
        )

    def _skill_setup_lines(self) -> list[str]:
        if not self.skills:
            return ["printf(\"[AutoRP] Brak umiejętności do wczytania\");"]
        return ["printf(\"[AutoRP] Dostępnych umiejętności: %d\", sizeof(gSkills));"]

    def _skill_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.skills:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        for index, skill in enumerate(self.skills):
            block = skill.command_block(index, prefix)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _skill_training_enum(self) -> str:
        entries = [training.constant for training in self.skill_trainings]
        entries.append("SKILL_TRAINING_COUNT")
        formatted = ",\n    ".join(entries)
        return "enum eSkillTrainingId {\n    " + formatted + "\n};"

    def _skill_training_data_enum(self) -> str:
        return "".join(
            [
                "enum eSkillTrainingData {\n",
                "    TrainingName[48],\n",
                "    TrainingDescription[128],\n",
                "    TrainingCommand[32],\n",
                "    TrainingSkillId,\n",
                "    TrainingXpGain,\n",
                "    TrainingCooldown,\n",
                "    TrainingSuccessMessage[96]\n",
                "};",
            ]
        )

    def _skill_training_definitions(self) -> str:
        if not self.skill_trainings:
            return "// Brak zdefiniowanych treningów umiejętności"
        skills = self.skill_lookup()
        entries = ",\n".join(
            training.array_entry(skills) for training in self.skill_trainings
        )
        return "new gSkillTrainings[][eSkillTrainingData] = {\n" + entries + "\n};"

    def _skill_training_setup_lines(self) -> list[str]:
        if not self.skill_trainings:
            return ["printf(\"[AutoRP] Brak treningów umiejętności\");"]
        return [
            "printf(\"[AutoRP] Zarejestrowano treningi: %d\", sizeof(gSkillTrainings));",
        ]

    def _skill_training_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.skill_trainings:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        for index, training in enumerate(self.skill_trainings):
            block = training.command_block(index, prefix)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _territory_enum(self) -> str:
        if not self.territories:
            return "enum eTerritoryId {\n    TERRITORY_COUNT = 0\n};"
        entries = [territory.constant for territory in self.territories] + [
            "TERRITORY_COUNT"
        ]
        formatted = ",\n    ".join(entries)
        return "enum eTerritoryId {\n    " + formatted + "\n};"

    def _territory_data_enum(self) -> str:
        return "".join(
            [
                "enum eTerritoryData {\n",
                "    TerritoryName[48],\n",
                "    TerritoryDescription[160],\n",
                "    Float:TerritoryX,\n",
                "    Float:TerritoryY,\n",
                "    Float:TerritoryZ,\n",
                "    Float:TerritoryRadius,\n",
                "    TerritoryOwnerFaction,\n",
                "    TerritoryIncome,\n",
                "    TerritoryCaptureTime,\n",
                "    TerritoryRewardMoney,\n",
                "    TerritoryInfoCommand[32],\n",
                "    TerritoryCaptureCommand[32],\n",
                "    TerritoryBroadcastMessage[160]\n",
                "};",
            ]
        )

    def _territory_definitions(self) -> str:
        if not self.territories:
            return "// Brak zdefiniowanych terytoriów"
        factions = self.faction_lookup()
        entries = ",\n".join(
            territory.array_entry(factions) for territory in self.territories
        )
        return "new gTerritories[][eTerritoryData] = {\n" + entries + "\n};"

    def _territory_setup_lines(self) -> list[str]:
        if not self.territories:
            return ["printf(\"[AutoRP] Brak terytoriów do zainicjalizowania\");"]
        lines: list[str] = []
        for index, territory in enumerate(self.territories):
            lines.append(
                f"    TerritoryOwners[{index}] = gTerritories[{index}][TerritoryOwnerFaction];"
            )
            lines.append(
                f"    TerritoryCaptureStarter[{index}] = INVALID_PLAYER_ID;"
            )
            lines.append(
                f'    printf("[AutoRP] Teren %s przygotowany", gTerritories[{index}][TerritoryName]);'
            )
        lines.append('    SetTimer("TickTerritories", 300000, true);')
        return lines

    def _territory_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.territories:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        for index, territory in enumerate(self.territories):
            info_block = territory.info_command_block(index, prefix)
            lines.extend(info_block)
            prefix = "else if"
            capture_block = territory.capture_command_block(index, prefix)
            lines.extend(capture_block)
            prefix = "else if"
        return lines

    def _law_violation_definitions(self) -> str:
        lines = [
            "enum eLawViolationData {",
            "    LawCode[16],",
            "    LawName[48],",
            "    LawDescription[160],",
            "    LawSeverity,",
            "    LawFine,",
            "    LawJailMinutes,",
            "    LawReputationPenalty",
            "};",
        ]
        entries = [violation.array_entry() for violation in self.law_violations]
        if not entries:
            array_lines = ["new gLawViolations[][eLawViolationData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gLawViolations[][eLawViolationData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _law_setup_lines(self) -> list[str]:
        lines: list[str] = []
        if self.law_violations:
            lines.append(
                'printf("[AutoRP] Zarejestrowano %d wykroczeń/kategorii przestępstw.", sizeof(gLawViolations));'
            )
        if self.patrol_routes:
            lines.append(
                'printf("[AutoRP] Dostępnych tras patrolowych: %d.", sizeof(gPatrolRoutes));'
            )
        if self.heists:
            lines.append(
                'printf("[AutoRP] Dostępnych napadów fabularnych: %d.", sizeof(gHeists));'
            )
        if not lines:
            return ['printf("[AutoRP] Brak rozszerzeń systemu prawa.");']
        return lines

    def _law_command_lines(self, initial_prefix: str) -> list[str]:
        prefix = initial_prefix
        lines: list[str] = []
        lawbook_trigger = escape_pawn_string("/kodeks")
        lines.extend(
            [
                f"{prefix}(!strcmp(cmdtext, \"{lawbook_trigger}\", true))",
                "{",
                "    ShowPlayerLawBook(playerid);",
                "    return 1;",
                "}",
            ]
        )
        prefix = "else if"
        wanted_trigger = escape_pawn_string("/wanted")
        lines.extend(
            [
                f"{prefix}(!strcmp(cmdtext, \"{wanted_trigger}\", true))",
                "{",
                "    ShowPlayerWantedLevel(playerid);",
                "    return 1;",
                "}",
            ]
        )
        if self.patrol_routes:
            stop_trigger = escape_pawn_string(self.patrol_stop_command)
            condition_prefix = "else if" if lines else prefix
            lines.extend(
                [
                    f"{condition_prefix}(!strcmp(cmdtext, \"{stop_trigger}\", true))",
                    "{",
                    "    StopPlayerPatrol(playerid);",
                    "    return 1;",
                    "}",
                ]
            )
        return lines

    def _patrol_point_array(self) -> str:
        if not self.patrol_routes:
            return "\n".join(
                [
                    "enum ePatrolPointData {",
                    "    PatrolPointX,",
                    "    PatrolPointY,",
                    "    PatrolPointZ,",
                    "    PatrolPointWait",
                    "};",
                    "new Float:gPatrolRoutePoints[][ePatrolPointData] = {};",
                ]
            )
        entries: list[str] = []
        for route in self.patrol_routes:
            entries.extend(point.array_entry() for point in route.points)
        body = ",\n".join(entries)
        return "\n".join(
            [
                "enum ePatrolPointData {",
                "    PatrolPointX,",
                "    PatrolPointY,",
                "    PatrolPointZ,",
                "    PatrolPointWait",
                "};",
                "new Float:gPatrolRoutePoints[][ePatrolPointData] = {",
                body,
                "};",
            ]
        )

    def _patrol_route_definitions(self) -> str:
        lines = [
            "enum ePatrolRouteData {",
            "    PatrolRouteName[48],",
            "    PatrolRouteFaction,",
            "    PatrolRoutePointStart,",
            "    PatrolRoutePointCount,",
            "    PatrolRouteLoop,",
            "    PatrolRouteCommand[32],",
            "    PatrolRouteRadio[96]",
            "};",
        ]
        if not self.patrol_routes:
            array_lines = ["new gPatrolRoutes[][ePatrolRouteData] = {};"]
        else:
            factions = self.faction_lookup()
            entries: list[str] = []
            point_start = 0
            for route in self.patrol_routes:
                entries.append(route.array_entry(factions, point_start))
                point_start += len(route.points)
            body = ",\n".join(entries)
            array_lines = [
                "new gPatrolRoutes[][ePatrolRouteData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _patrol_route_setup_lines(self) -> list[str]:
        if not self.patrol_routes:
            return ['printf("[AutoRP] Brak tras patrolowych.");']
        return [
            'printf("[AutoRP] Zarejestrowano trasy patrolowe: %d.", sizeof(gPatrolRoutes));',
        ]

    def _patrol_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.patrol_routes:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        factions = self.faction_lookup()
        for index, route in enumerate(self.patrol_routes):
            block = route.command_block(index, prefix, factions)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _heist_stage_definitions(self) -> str:
        lines = [
            "enum eHeistStageData {",
            "    HeistStageDescription[160],",
            "    HeistStageTimeLimit,",
            "    HeistStageSuccessMessage[96],",
            "    HeistStageFailureMessage[96]",
            "};",
        ]
        entries = [
            stage.array_entry()
            for heist in self.heists
            for stage in heist.stages
        ]
        if not entries:
            array_lines = ["new gHeistStages[][eHeistStageData] = {};"]
        else:
            body = ",\n".join(entries)
            array_lines = [
                "new gHeistStages[][eHeistStageData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _heist_definitions(self) -> str:
        lines = [
            "enum eHeistData {",
            "    HeistName[48],",
            "    HeistLocation[96],",
            "    HeistCooldownMinutes,",
            "    HeistRequiredPlayers,",
            "    HeistStageStart,",
            "    HeistStageCount,",
            "    HeistRewardMoney,",
            "    HeistRewardItem[32],",
            "    HeistRewardReputation,",
            "    HeistRequiredItems[96],",
            "    HeistFaction,",
            "    HeistAnnouncement[128]",
            "};",
        ]
        if not self.heists:
            array_lines = ["new gHeists[][eHeistData] = {};"]
        else:
            factions = self.faction_lookup()
            entries: list[str] = []
            stage_start = 0
            for heist in self.heists:
                entries.append(heist.array_entry(factions, stage_start))
                stage_start += len(heist.stages)
            body = ",\n".join(entries)
            array_lines = [
                "new gHeists[][eHeistData] = {",
                body,
                "};",
            ]
        return "\n".join(lines + array_lines)

    def _heist_setup_lines(self) -> list[str]:
        if not self.heists:
            return ['printf("[AutoRP] Brak aktywnych scenariuszy napadów.");']
        return [
            'printf("[AutoRP] Zarejestrowano napady fabularne: %d.", sizeof(gHeists));',
        ]

    def _heist_command_lines(self, initial_prefix: str) -> list[str]:
        if not self.heists:
            return []
        prefix = initial_prefix
        lines: list[str] = []
        factions = self.faction_lookup()
        for index, heist in enumerate(self.heists):
            block = heist.command_block(index, prefix, factions)
            lines.extend(block)
            prefix = "else if"
        return lines

    def _weather_stage_definitions(self) -> str:
        lines = [
            "enum eWeatherStageData {",
            "    WeatherStageHour,",
            "    WeatherStageWeather,",
            "    WeatherStageDurationMinutes,",
            "    WeatherStageDescription[64]",
            "};",
        ]
        if not self.weather_cycle:
            array_lines = ["new gWeatherStages[][eWeatherStageData] = {};"]
        else:
            array_lines = [self.weather_cycle.array_definition()]
        return "\n".join(lines + array_lines)

    def _weather_setup_lines(self) -> list[str]:
        if not self.weather_cycle:
            return ["printf(\"[AutoRP] Korzystanie z statycznych ustawień pogody\");"]
        return self.weather_cycle.setup_lines()

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

    def bot_automation_plan(self) -> BotAutomationPlan | None:
        if not self.bot_clients and not self.bot_runs:
            return None
        return BotAutomationPlan(clients=tuple(self.bot_clients), runs=tuple(self.bot_runs))

    def bot_run_contexts(self) -> list[BotRunContext]:
        plan = self.bot_automation_plan()
        if plan is None:
            return []
        return plan.contexts(self.scenarios)

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
            "quests": [quest.name for quest in self.quests],
            "businesses": [business.name for business in self.businesses],
            "crafting_recipes": [recipe.name for recipe in self.crafting_recipes],
            "achievements": [achievement.name for achievement in self.achievements],
            "skills": [skill.name for skill in self.skills],
            "skill_trainings": [training.name for training in self.skill_trainings],
            "territories": [territory.name for territory in self.territories],
            "law_violations": [violation.code for violation in self.law_violations],
            "patrol_routes": [route.name for route in self.patrol_routes],
            "heists": [heist.name for heist in self.heists],
            "weather_cycle": [stage.weather for stage in self.weather_cycle.stages]
            if self.weather_cycle
            else [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def pawn_context(self) -> dict:
        property_pickup_handlers = indent_lines(
            self._property_pickup_handlers(), level=1
        )
        business_pickup_handlers = indent_lines(
            self._business_pickup_function_lines(), level=1
        )
        event_handlers = self._event_handlers()
        if event_handlers:
            event_handlers += "\n"
        skill_count = len(self.skills)
        skill_training_count = len(self.skill_trainings)
        skill_max_levels = self._max_skill_levels()
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
            "quest_enum": self._quest_enum(),
            "quest_definitions": self._quest_definitions(),
            "quest_step_definitions": self._quest_step_definitions(),
            "quest_step_offsets": self._quest_step_offsets(),
            "quest_setup": indent_lines(self._quest_setup_lines(), level=1),
            "business_enum": self._business_enum(),
            "business_definitions": self._business_definitions(),
            "business_pickup_array": self._business_pickup_array(),
            "business_setup": indent_lines(self._business_setup_lines(), level=1),
            "business_pickup_handlers": business_pickup_handlers,
            "npc_enum": self._npc_enum(),
            "npc_actor_array": self._npc_actor_array(),
            "npc_setup": indent_lines(self._npc_setup_lines(), level=1),
            "crafting_definitions": self._crafting_definitions(),
            "crafting_setup": indent_lines(self._crafting_setup_lines(), level=1),
            "achievement_enum": self._achievement_enum(),
            "achievement_definitions": self._achievement_definitions(),
            "achievement_setup": indent_lines(self._achievement_setup_lines(), level=1),
            "skill_count": skill_count,
            "skill_max_levels": skill_max_levels,
            "skill_training_count": skill_training_count,
            "skill_enum": self._skill_enum(),
            "skill_data_enum": self._skill_data_enum(),
            "skill_definitions": self._skill_definitions(),
            "skill_level_requirements": self._skill_level_requirements(),
            "skill_reward_messages": self._skill_reward_messages(),
            "skill_setup": indent_lines(self._skill_setup_lines(), level=1),
            "skill_training_enum": self._skill_training_enum(),
            "skill_training_data_enum": self._skill_training_data_enum(),
            "skill_training_definitions": self._skill_training_definitions(),
            "skill_training_setup": indent_lines(
                self._skill_training_setup_lines(), level=1
            ),
            "territory_enum": self._territory_enum(),
            "territory_data_enum": self._territory_data_enum(),
            "territory_definitions": self._territory_definitions(),
            "territory_setup": indent_lines(
                self._territory_setup_lines(), level=1
            ),
            "law_violation_count": len(self.law_violations),
            "law_violation_definitions": self._law_violation_definitions(),
            "law_setup": indent_lines(self._law_setup_lines(), level=1),
            "patrol_route_count": len(self.patrol_routes),
            "patrol_point_definitions": self._patrol_point_array(),
            "patrol_route_definitions": self._patrol_route_definitions(),
            "patrol_setup": indent_lines(self._patrol_route_setup_lines(), level=1),
            "patrol_stop_command": escape_pawn_string(self.patrol_stop_command),
            "heist_count": len(self.heists),
            "heist_definitions": self._heist_definitions(),
            "heist_stage_definitions": self._heist_stage_definitions(),
            "heist_setup": indent_lines(self._heist_setup_lines(), level=1),
            "weather_stage_definitions": self._weather_stage_definitions(),
            "weather_setup": indent_lines(self._weather_setup_lines(), level=1),
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
    "Quest",
    "QuestStep",
    "Business",
    "CraftingRecipe",
    "CraftingIngredient",
    "Achievement",
    "Skill",
    "SkillLevel",
    "SkillTraining",
    "Territory",
    "LawViolation",
    "PatrolRoute",
    "PatrolPoint",
    "Heist",
    "HeistStage",
    "WeatherStage",
    "WeatherCycle",
    "BotScenarioDefinition",
    "BotClientLogDefinition",
    "BotClientDefinition",
    "BotClientLogExpectationDefinition",
    "BotRunDefinition",
    "BotAutomationPlan",
]
