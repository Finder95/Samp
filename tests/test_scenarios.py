import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.autorp.scenario import BotScenarioSpec, BotScriptMacro, ScenarioStep


def test_scenario_step_normalisation():
    raw = {"type": "chat", "message": "Cześć"}
    step = ScenarioStep.from_dict(raw)
    assert step.type == "chat"
    assert step.payload["message"] == "Cześć"
    assert step.to_command() == "CHAT:Cześć"


def test_bot_scenario_to_script():
    spec = BotScenarioSpec(
        name="test",
        description="Opis",
        steps=[
            {"type": "command", "value": "sluzba"},
            "pomoc",
            {"type": "wait", "seconds": 2},
        ],
    )
    script = spec.to_bot_script()
    assert script.description == "Opis"
    assert script.commands[0] == "/sluzba"
    assert script.commands[1] == "/pomoc"
    assert any(action["type"] == "wait" for action in script.actions)


def test_bot_scenario_macro_expansion():
    macro = BotScriptMacro(
        name="announce",
        parameters=("target",),
        steps=(
            {"type": "chat", "message": "Hej {{target}}"},
            {"type": "wait", "seconds": 0.5},
        ),
    )
    spec = BotScenarioSpec(
        name="macro",
        description="Makro",
        steps=[
            {"type": "macro", "name": "announce", "arguments": {"target": "Gracz"}},
            {"type": "command", "value": "status {{state}}"},
        ],
        macros={"announce": macro},
        variables={"state": "online"},
    )
    script = spec.to_bot_script()
    assert script.actions[0]["message"] == "Hej Gracz"
    assert script.actions[1]["seconds"] == 0.5
    assert script.actions[2]["command"] == "/status online"
