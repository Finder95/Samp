import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.autorp.bots import (
    BufferedCommandTransport,
    DummyBotClient,
    FileCommandTransport,
    ScriptRunner,
    WineSampClient,
)
from tools.autorp.config import GamemodeConfig
from tools.autorp.tester import BotRunContext, BotScript, TestOrchestrator


def test_bot_script_iter_actions_prefers_actions():
    script = BotScript(
        description="test",
        commands=("/komenda",),
        actions=(
            {"type": "chat", "message": "Cześć"},
            {"type": "wait", "seconds": 1.0},
        ),
    )
    actions = script.iter_actions()
    assert len(actions) == 2
    assert actions[0].type == "chat"
    assert actions[1].delay == 1.0


def test_script_runner_records_payloads(tmp_path):
    command_file = tmp_path / "commands.txt"
    transport = FileCommandTransport(command_file)
    runner = ScriptRunner(transport, sleep=lambda _: None)
    script = BotScript(
        description="Playback",
        actions=(
            {"type": "chat", "message": "Hej"},
            {"type": "wait", "seconds": 0.5},
            {"type": "command", "command": "/pomoc"},
        ),
    )
    log = runner.run(script)
    assert command_file.read_text(encoding="utf-8").strip().splitlines() == [
        "CHAT Hej",
        "WAIT:0.5",
        "/pomoc",
    ]
    assert len(log.events) == 3
    assert log.events[0].command_payloads[0] == "CHAT Hej"


def test_action_translator_supports_extended_actions():
    transport = BufferedCommandTransport()
    runner = ScriptRunner(transport, sleep=lambda _: None)
    script = BotScript(
        description="Extended",
        actions=(
            {"type": "keypress", "key": "f"},
            {"type": "macro", "commands": ["/one", "/two"]},
            {"type": "wait_for", "phrase": "Connected", "timeout": 3},
        ),
    )
    log = runner.run(script)
    assert transport.buffer == [
        "KEY:F:down",
        "KEY:F:up",
        "/one",
        "/two",
        "WAITFOR:3.0:Connected",
    ]
    assert len(log.events) == 3


def test_orchestrator_returns_logs(tmp_path):
    transport = BufferedCommandTransport()
    client = DummyBotClient(name="dummy", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Scenario", commands=("/wave",))
    result = orchestrator.run(script, server_address="127.0.0.1:7777")
    assert result.successful_clients() == ["dummy"]
    assert transport.buffer == ["/wave"]
    assert result.log_expectations == ()


def test_wine_client_dry_run(tmp_path):
    gta_dir = tmp_path / "gta"
    gta_dir.mkdir()
    client = WineSampClient(
        name="wine-bot",
        gta_directory=gta_dir,
        dry_run=True,
    )
    client.connect("127.0.0.1:7777")
    script = BotScript(description="DryRun", commands=("/start",))
    log = client.execute_script(script)
    assert log.commands_sent() == ["/start"]
    assert client.command_file.exists()


def test_run_suite_filters_clients(tmp_path):
    transport_a = BufferedCommandTransport()
    transport_b = BufferedCommandTransport()
    client_a = DummyBotClient(name="alpha", transport=transport_a)
    client_b = DummyBotClient(name="beta", transport=transport_b)
    orchestrator = TestOrchestrator(clients=[client_a, client_b])
    script = BotScript(description="Filtered", commands=("/onlybeta",))
    context = BotRunContext(script=script, client_names=("beta",))
    results = orchestrator.run_suite([context], server_address="127.0.0.1:7777")
    assert len(results) == 1
    assert results[0].successful_clients() == ["beta"]
    assert transport_a.buffer == []
    assert transport_b.buffer == ["/onlybeta"]


def test_config_bot_plan_contexts():
    data = {
        "name": "Demo",
        "description": "Test",
        "author": "QA",
        "bot_scenarios": [
            {
                "name": "simple",
                "description": "Simple",
                "steps": ["/hello"],
            }
        ],
        "bot_automation": {
            "clients": [{"name": "dummy", "type": "dummy"}],
            "runs": [
                {
                    "scenario": "simple",
                    "clients": ["dummy"],
                    "iterations": 2,
                }
            ],
        },
    }
    config = GamemodeConfig.from_dict(data)
    plan = config.bot_automation_plan()
    assert plan is not None
    contexts = plan.contexts(config.scenarios)
    assert len(contexts) == 1
    assert contexts[0].client_names == ("dummy",)
    assert contexts[0].iterations == 2
