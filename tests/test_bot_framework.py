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
    WineWindowInteractor,
)
from tools.autorp.config import GamemodeConfig
from tools.autorp.tester import (
    BotRunContext,
    BotScript,
    ClientLogExpectation,
    ClientLogExpectationResult,
    ClientLogMonitor,
    ClientLogExportRequest,
    ClientRunResult,
    LogExpectationResult,
    RunFailure,
    RunAssertionResult,
    RunAssertionRule,
    ScenarioStatistics,
    ServerLogExpectation,
    ServerLogMonitor,
    TestOrchestrator,
    TestRunResult,
)


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
            {"type": "focus_window"},
            {"type": "type_text", "text": "login"},
            {"type": "mouse_move", "x": 120, "y": 220, "duration": 0.1},
            {"type": "mouse_click", "button": "left", "state": "double"},
            {"type": "screenshot", "name": "after_login"},
            {"type": "config", "name": "sensitivity", "value": 0.5},
            {"type": "key_sequence", "keys": ["f", "enter"], "interval": 0.1},
            {"type": "mouse_scroll", "direction": "up", "steps": 2},
            {
                "type": "mouse_drag",
                "start_x": 1,
                "start_y": 2,
                "end_x": 3,
                "end_y": 4,
                "duration": 0.05,
                "hold": 0.02,
            },
            {"type": "key_combo", "keys": ["ctrl", "s"], "hold": 0.1},
        ),
    )
    log = runner.run(script)
    assert transport.buffer == [
        "KEY:F:down",
        "KEY:F:up",
        "/one",
        "/two",
        "WAITFOR:3.0:Connected",
        "FOCUS",
        "TYPE:login",
        "MOUSE:absolute:120.0:220.0:0.1",
        "MOUSECLICK:left:double",
        "SCREENSHOT:after_login",
        "CONFIG:sensitivity=0.5",
        "KEY:F:down",
        "KEY:F:up",
        "WAIT:0.1",
        "KEY:ENTER:down",
        "KEY:ENTER:up",
        "MOUSESCROLL:up:2:0",
        "MOUSE:absolute:1.0:2.0:0.05",
        "MOUSECLICK:left:down",
        "WAIT:0.02",
        "MOUSE:absolute:3.0:4.0:0.05",
        "MOUSECLICK:left:up",
        "KEY:CTRL:down",
        "KEY:S:down",
        "WAIT:0.1",
        "KEY:S:up",
        "KEY:CTRL:up",
    ]
    assert len(log.events) == 13


def test_orchestrator_returns_logs(tmp_path):
    transport = BufferedCommandTransport()
    client = DummyBotClient(name="dummy", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Scenario", commands=("/wave",))
    result = orchestrator.run(script, server_address="127.0.0.1:7777")
    assert result.successful_clients() == ["dummy"]
    assert transport.buffer == ["/wave"]
    assert result.log_expectations == ()
    assert result.is_successful()
    assert result.failures == ()
    assert result.attempt_index == 1
    assert result.duration is not None and result.duration >= 0.0


def test_orchestrator_assertions_and_failures():
    transport = BufferedCommandTransport()
    client = DummyBotClient(name="dummy", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Assert", commands=("/hi", "/bye"))
    ok_result = orchestrator.run(
        script,
        server_address="127.0.0.1:7777",
        assertions=(
            RunAssertionRule(type="total_duration", max_value=5.0, name="duration"),
            RunAssertionRule(
                type="command_count", client_name="dummy", min_value=2, max_value=2
            ),
            RunAssertionRule(type="require_log", client_name="dummy"),
        ),
    )
    assert ok_result.is_successful()
    assert ok_result.assertions
    assert all(assertion.passed for assertion in ok_result.assertions)

    fail_result = orchestrator.run(
        script,
        server_address="127.0.0.1:7777",
        assertions=(RunAssertionRule(type="command_count", min_value=5, name="too many"),),
    )
    assert not fail_result.is_successful()
    assert fail_result.assertions
    assert any(not assertion.passed for assertion in fail_result.assertions)
    assert any(failure.category == "assertion" for failure in fail_result.failures)


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
    assert client.client_log_monitors()


def test_wine_window_interactor_records_commands():
    interactor = WineWindowInteractor(window_title="Test", dry_run=True, dry_run_window_id="0xabc")
    interactor.focus()
    interactor.type_text("Hello")
    interactor.mouse_move(50, 60, duration=0.2)
    interactor.mouse_click("left", "double")
    interactor.mouse_scroll("up", steps=3)
    interactor.key_event("enter")
    interactor.key_event("lshift", "down")
    interactor.key_event("lshift", "up")
    assert interactor.executed_commands[0] == ["xdotool", "search", "--name", "Test"]
    assert interactor.executed_commands[1][1] == "windowactivate"
    assert any(command[1] == "type" for command in interactor.executed_commands if len(command) > 1)
    assert any("click" in command for command in interactor.executed_commands[-4:])
    assert any(
        cmd[1] in {"keydown", "keyup", "key"}
        for cmd in interactor.executed_commands
        if len(cmd) > 1
    )


def test_wine_client_window_interactions(tmp_path):
    gta_dir = tmp_path / "gta"
    chat_dir = gta_dir / "SAMP"
    chat_dir.mkdir(parents=True)
    client = WineSampClient(
        name="wine-extended",
        gta_directory=gta_dir,
        dry_run=True,
        focus_window=True,
        log_files=(("custom", tmp_path / "custom.log", "utf-8"),),
        setup_actions=({"type": "wait", "seconds": 0.1},),
        teardown_actions=({"type": "wait", "seconds": 0.2},),
    )
    client.connect("127.0.0.1:7777")
    script = BotScript(
        description="WindowActions",
        actions=(
            {"type": "focus_window", "title": "Custom"},
            {"type": "type_text", "text": "hello"},
            {"type": "mouse_move", "x": 10, "y": 20},
            {"type": "mouse_click", "button": "left", "state": "double"},
            {"type": "screenshot", "name": "after", "path": "captures/after.png"},
            {"type": "key_sequence", "keys": ["enter"]},
            {"type": "mouse_scroll", "direction": "down", "steps": 1},
        ),
    )
    client.execute_script(script)
    assert client.window_interactor is not None
    commands = client.window_interactor.executed_commands
    assert any("Custom" in " ".join(cmd) for cmd in commands)
    assert any(cmd[1] == "type" for cmd in commands if len(cmd) > 1)
    assert any(cmd[1] in {"click", "keydown"} for cmd in commands if len(cmd) > 1)
    screenshots = client.captured_screenshots
    assert screenshots and screenshots[0].name == "after.png"
    monitors = client.client_log_monitors()
    assert sorted(monitor.name for monitor in monitors) == ["chatlog", "custom"]


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


def test_orchestrator_client_log_expectations(tmp_path):
    log_path = tmp_path / "chatlog.txt"
    log_path.write_text("", encoding="utf-8")

    class WritingClient(DummyBotClient):
        def execute_script(self, script: BotScript):  # type: ignore[override]
            result = super().execute_script(script)
            log_path.write_text(log_path.read_text(encoding="utf-8") + "Connected\n", encoding="utf-8")
            return result

    monitor = ClientLogMonitor(client_name="dummy", name="chatlog", log_path=log_path)
    transport = BufferedCommandTransport()
    client = WritingClient(name="dummy", transport=transport, log_monitors=(monitor,))
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Logs", commands=("/wave",))
    expectation = ClientLogExpectation(client_name="dummy", phrase="Connected", log_name="chatlog", timeout=0.5, poll_interval=0.05)
    result = orchestrator.run(
        script,
        server_address="127.0.0.1:7777",
        client_names=("dummy",),
        client_log_expectations=(expectation,),
    )
    assert result.client_log_expectations
    assert result.client_log_expectations[0].matched is True
    assert result.failures == ()
    assert result.is_successful()


def test_orchestrator_records_playback_and_screenshots(tmp_path):
    shot_path = tmp_path / "shot.png"

    class RecordingClient(DummyBotClient):
        def execute_script(self, script: BotScript):  # type: ignore[override]
            log = super().execute_script(script)
            self.captured_screenshots = [shot_path]
            return log

    transport = BufferedCommandTransport()
    client = RecordingClient(name="recording", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Record Demo", commands=("/action",))
    record_dir = tmp_path / "playback"
    result = orchestrator.run(
        script,
        server_address="127.0.0.1:7777",
        record_playback_dir=record_dir,
    )
    assert record_dir.exists()
    client_result = result.client_results[0]
    assert client_result.playback_log_path is not None
    assert client_result.playback_log_path.exists()
    assert client_result.screenshots == (shot_path,)
    assert result.is_successful()


def test_register_script_slugifies_and_deduplicates(tmp_path):
    transport = BufferedCommandTransport()
    client = DummyBotClient(name="dummy", transport=transport)
    orchestrator = TestOrchestrator(clients=[client], scripts_dir=tmp_path)
    script = BotScript(
        description="Patrol: Downtown / #1",
        commands=("/start",),
    )
    saved_path = orchestrator.register_script(script)
    assert saved_path.parent == tmp_path
    assert saved_path.name.startswith("patrol_downtown_1")
    duplicate = orchestrator.register_script(script)
    assert duplicate.parent == tmp_path
    assert duplicate != saved_path
    assert duplicate.name.startswith("patrol_downtown_1")
    anonymous = BotScript(description="  ", commands=("/a",))
    anon_path = orchestrator.register_script(anonymous)
    assert anon_path.name.startswith("scenario")


def test_orchestrator_exports_logs(tmp_path):
    server_log_path = tmp_path / "server_log.txt"
    server_log_path.write_text("", encoding="utf-8")
    client_log_path = tmp_path / "client_log.txt"
    client_log_path.write_text("", encoding="utf-8")

    class ExportingClient(DummyBotClient):
        def execute_script(self, script: BotScript):  # type: ignore[override]
            result = super().execute_script(script)
            client_log_path.write_text(
                client_log_path.read_text(encoding="utf-8") + "client ready\n",
                encoding="utf-8",
            )
            server_log_path.write_text(
                server_log_path.read_text(encoding="utf-8") + "player joined\n",
                encoding="utf-8",
            )
            return result

    client_monitor = ClientLogMonitor(
        client_name="exporter",
        name="chatlog",
        log_path=client_log_path,
    )
    transport = BufferedCommandTransport()
    client = ExportingClient(name="exporter", transport=transport, log_monitors=(client_monitor,))

    server_monitor = ServerLogMonitor(server_log_path)

    class DummyController:
        def __init__(self):
            self.server_address = "127.0.0.1:7777"
            self.log_monitor = server_monitor

        class _Context:
            def __init__(self, outer):
                self._outer = outer

            def __enter__(self):
                server_log_path.write_text("", encoding="utf-8")
                return self._outer

            def __exit__(self, exc_type, exc, tb):
                return False

        def running(self, timeout: float = 20.0):
            return self._Context(self)

    orchestrator = TestOrchestrator(
        clients=[client],
        server_controller=DummyController(),
    )
    script = BotScript(description="ExportFlow", commands=("/ready",))
    context = BotRunContext(
        script=script,
        capture_server_log=True,
        server_log_export=tmp_path / "server_export.log",
        client_log_exports=(
            ClientLogExportRequest(
                client_name="exporter",
                log_name="chatlog",
                target_path=tmp_path / "client_export.log",
            ),
        ),
    )
    result = orchestrator.run_suite([context])[0]
    assert "player joined" in (result.server_log_excerpt or "")
    assert result.server_log_path is not None and result.server_log_path.exists()
    assert result.server_log_path.read_text(encoding="utf-8").strip() == "player joined"
    assert result.client_log_exports
    export_result = result.client_log_exports[0]
    assert export_result.target_path is not None and export_result.target_path.exists()
    assert "client ready" in export_result.target_path.read_text(encoding="utf-8")
    assert client_log_path.read_text(encoding="utf-8").strip().endswith("client ready")
    assert result.is_successful()
    assert result.failures == ()


def test_run_suite_retries_until_success():
    attempts = {"count": 0}
    transport = BufferedCommandTransport()

    class FlakyClient(DummyBotClient):
        def execute_script(self, script: BotScript):  # type: ignore[override]
            attempts["count"] += 1
            if attempts["count"] < 2:
                return None
            return super().execute_script(script)

    client = FlakyClient(name="flaky", transport=transport)
    orchestrator = TestOrchestrator(clients=[client])
    script = BotScript(description="Retry", commands=("/retry",))
    context = BotRunContext(script=script, max_retries=2)
    results = orchestrator.run_suite([context], server_address="127.0.0.1:7777")
    assert len(results) == 2
    assert results[0].is_successful() is False
    assert any(failure.category == "client" for failure in results[0].failures)
    assert results[0].attempt_index == 1
    assert results[1].is_successful()
    assert results[1].attempt_index == 2


def test_run_suite_fail_fast_breaks_execution(tmp_path):
    log_path = tmp_path / "client.log"
    log_path.write_text("", encoding="utf-8")
    monitor = ClientLogMonitor(client_name="dummy", name="chatlog", log_path=log_path)
    transport = BufferedCommandTransport()
    client = DummyBotClient(name="dummy", transport=transport, log_monitors=(monitor,))
    orchestrator = TestOrchestrator(clients=[client])
    failing_expectation = ClientLogExpectation(
        client_name="dummy", phrase="expected", log_name="chatlog", timeout=0.1, poll_interval=0.01
    )
    fail_context = BotRunContext(
        script=BotScript(description="Fail", commands=("/fail",)),
        client_names=("dummy",),
        client_log_expectations=(failing_expectation,),
        fail_fast=True,
    )
    ok_context = BotRunContext(script=BotScript(description="OK", commands=("/ok",)))
    results = orchestrator.run_suite([fail_context, ok_context], server_address="127.0.0.1:7777")
    assert len(results) == 1
    assert not results[0].is_successful()
    assert any(failure.category == "client_log" for failure in results[0].failures)


def test_config_bot_plan_contexts():
    data = {
        "name": "Demo",
        "description": "Test",
        "author": "QA",
        "bot_macros": [
            {
                "name": "greet",
                "parameters": ["player"],
                "steps": [
                    {"type": "chat", "message": "Witaj {{player}}"},
                    {"type": "wait", "seconds": 0.2},
                ],
            }
        ],
        "bot_variables": {"code": "S1"},
        "bot_scenarios": [
            {
                "name": "simple",
                "description": "Simple",
                "variables": {"player": "Scenario"},
                "macros": [
                    {
                        "name": "prepare",
                        "steps": [{"type": "command", "value": "prep"}],
                    }
                ],
                "steps": [
                    {"type": "macro", "name": "greet", "arguments": {"player": "Tester"}},
                    {"type": "macro", "name": "prepare"},
                    {"type": "command", "value": "use {{code}}"},
                ],
            }
        ],
        "bot_automation": {
            "variables": {"code": "AUTO"},
            "clients": [
                {
                    "name": "dummy",
                    "type": "dummy",
                    "logs": [{"name": "custom", "path": "logs/custom.log"}],
                    "setup_actions": [{"type": "wait", "seconds": 0.5}],
                    "focus_window": True,
                }
            ],
            "runs": [
                {
                    "scenario": "simple",
                    "clients": ["dummy"],
                    "iterations": 2,
                    "expect_server_logs": [
                        {
                            "phrase": "Tester joined",
                            "occurrences": 2,
                            "timeout": 1.5,
                        }
                    ],
                    "expect_client_logs": [{"client": "dummy", "phrase": "ready"}],
                    "wait_before": 0.25,
                    "record_playback_dir": "artifacts/playback",
                    "collect_server_log": True,
                    "server_log_export": "artifacts/server.log",
                    "export_client_logs": [
                        {
                            "client": "dummy",
                            "log": "custom",
                            "target": "artifacts/custom.log",
                            "include_full": True,
                        }
                    ],
                    "tags": ["smoke", "patrol"],
                    "retries": 2,
                    "grace_period": 0.75,
                    "fail_fast": True,
                    "enabled": True,
                    "assertions": [
                        {
                            "type": "command_count",
                            "client": "dummy",
                            "min": 2,
                            "max": 4,
                            "name": "dummy commands",
                        },
                        {
                            "type": "total_duration",
                            "max": 10,
                            "message": "Scenariusz przekroczył budżet czasowy",
                        },
                    ],
                }
            ],
        },
    }
    config = GamemodeConfig.from_dict(data)
    plan = config.bot_automation_plan()
    assert plan is not None
    assert plan.clients[0].logs[0].name == "custom"
    contexts = plan.contexts(
        config.scenarios, macros=config.bot_macros, global_variables=config.bot_variables
    )
    assert len(contexts) == 1
    context = contexts[0]
    assert context.client_names == ("dummy",)
    assert context.iterations == 2
    assert context.client_log_expectations[0].phrase == "ready"
    assert context.wait_before == 0.25
    assert context.record_playback_dir == Path("artifacts/playback")
    assert context.capture_server_log is True
    assert context.server_log_export == Path("artifacts/server.log")
    assert context.client_log_exports[0].include_full_log is True
    assert context.client_log_exports[0].target_path == Path("artifacts/custom.log")
    assert context.tags == ("smoke", "patrol")
    assert context.max_retries == 2
    assert context.grace_period == 0.75
    assert context.fail_fast is True
    assert context.enabled is True
    assert context.expect_server_logs[0].phrase == "Tester joined"
    assert context.expect_server_logs[0].occurrences == 2
    assert context.expect_server_logs[0].timeout == 1.5
    assert len(context.assertions) == 2
    assert context.assertions[0].type == "command_count"
    assert context.assertions[0].client_name == "dummy"
    actions = context.script.actions
    assert actions[0]["message"] == "Witaj Tester"
    assert actions[1]["type"] == "wait"
    assert actions[2]["command"] == "/prep"
    assert actions[3]["command"] == "/use AUTO"


def test_server_log_expectation_counts(tmp_path):
    log_path = tmp_path / "server_log.txt"
    log_path.write_text("", encoding="utf-8")
    monitor = ServerLogMonitor(log_path)
    monitor.mark()
    expectation = ServerLogExpectation(
        phrase="connected",
        occurrences=2,
        timeout=0.1,
        poll_interval=0.01,
        case_sensitive=False,
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("Player connected\n")
        handle.write("Another CONNECTED\n")
    matches = monitor.wait_for_expectation(expectation, timeout=0.2)
    assert matches == 2
    monitor.mark()
    regex_expectation = ServerLogExpectation(
        phrase=r"Player \d+",
        match_type="regex",
        timeout=0.1,
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("Player 42 joined\n")
    regex_matches = monitor.wait_for_expectation(regex_expectation, timeout=0.2)
    assert regex_matches == 1


def test_orchestrator_summarise_results_compiles_statistics():
    base_script = BotScript(description="Summary Demo")
    successful = TestRunResult(
        script=base_script,
        client_results=(ClientRunResult(client_name="alpha", log=None),),
        duration=2.5,
        assertions=(
            RunAssertionResult(name="duration", passed=True, actual=2.5, expected={}),
        ),
    )
    failing = TestRunResult(
        script=BotScript(description="Failing"),
        client_results=(ClientRunResult(client_name="beta", log=None),),
        log_expectations=(LogExpectationResult(phrase="ready", matched=False),),
        client_log_expectations=(
            ClientLogExpectationResult(
                client_name="beta", log_name="chat", phrase="connected", matched=False
            ),
        ),
        failures=(RunFailure(category="assertion", subject="duration", message="too slow"),),
        assertions=(
            RunAssertionResult(
                name="duration", passed=False, actual=10.0, expected={"max": 5.0}, message="too slow"
            ),
        ),
        duration=5.0,
    )

    stats = TestOrchestrator.summarise_results([successful, failing])
    assert stats.total_runs == 2
    assert stats.successful_runs == 1
    assert stats.failed_runs == 1
    assert stats.success_rate == 0.5
    assert stats.total_duration == 7.5
    assert stats.average_duration == 3.75
    assert stats.shortest_duration == 2.5
    assert stats.longest_duration == 5.0
    assert stats.assertion_failures == 1
    assert stats.log_expectation_failures == 1
    assert stats.client_log_expectation_failures == 1
    assert stats.failure_categories == {"assertion": 1}


def test_orchestrator_summarise_per_script_groups_attempts():
    primary_script = BotScript(description="Retry Demo")
    attempt_one = TestRunResult(
        script=primary_script,
        client_results=(ClientRunResult(client_name="alpha", log=None),),
        attempt_index=1,
        duration=3.0,
        failures=(
            RunFailure(category="network", subject="connect", message="timeout"),
        ),
    )
    attempt_two = TestRunResult(
        script=primary_script,
        client_results=(ClientRunResult(client_name="alpha", log=None),),
        attempt_index=2,
        duration=4.0,
    )
    other = TestRunResult(
        script=BotScript(description="Stable"),
        client_results=(ClientRunResult(client_name="beta", log=None),),
        duration=2.0,
    )

    summaries = TestOrchestrator.summarise_per_script([attempt_one, attempt_two, other])
    assert set(summaries) == {"Retry Demo", "Stable"}
    retry_stats = summaries["Retry Demo"]
    assert isinstance(retry_stats, ScenarioStatistics)
    assert retry_stats.total_runs == 2
    assert retry_stats.successful_runs == 1
    assert retry_stats.failed_runs == 1
    assert retry_stats.retries == 1
    assert retry_stats.flaky_successes == 1
    assert retry_stats.total_duration == 7.0
    assert retry_stats.average_duration == 3.5
    assert retry_stats.last_status == "SUCCESS"
    assert retry_stats.failure_categories == {"network": 1}

    stable_stats = summaries["Stable"]
    assert stable_stats.total_runs == 1
    assert stable_stats.retries == 0
    assert stable_stats.failure_categories == {}
