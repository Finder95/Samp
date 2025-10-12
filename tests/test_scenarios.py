import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.autorp.scenario import BotScenarioSpec, ScenarioStep


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
