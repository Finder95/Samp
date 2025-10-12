import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.autorp.bots import DummyBotClient, FileCommandTransport, ScriptRunner, WineSampClient
from tools.autorp.tester import BotScript, TestOrchestrator


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


def test_orchestrator_returns_logs(tmp_path):
    command_file = tmp_path / "commands.log"
    transport = FileCommandTransport(command_file)
    client = DummyBotClient(name="dummy", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Scenario", commands=("/wave",))
    result = orchestrator.run(script, server_address="127.0.0.1:7777")
    assert result.successful_clients() == ["dummy"]
    assert command_file.read_text(encoding="utf-8").strip() == "/wave"


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
