"""Command line interface for AutoRP utilities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bots import BufferedCommandTransport, DummyBotClient, FileCommandTransport, WineSampClient
from .config import BotClientDefinition, GamemodeConfig
from .generator import GamemodeGenerator
from .slug import slugify_description
from .tester import BotRunContext, SampServerController, TestOrchestrator


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoRP gamemode generator")
    parser.add_argument("config", type=Path, help="Ścieżka do pliku konfiguracyjnego JSON")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated"),
        help="Katalog, w którym powstanie gamemode",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=None,
        help="Opcjonalny katalog z własnymi szablonami",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=None,
        help="Przygotuj kompletną paczkę serwerową w podanym katalogu",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Po wygenerowaniu skompiluj gamemode do pliku AMX",
    )
    parser.add_argument(
        "--pawn-compiler",
        type=Path,
        default=None,
        help="Ścieżka do binarki pawncc (jeśli nie jest w PATH)",
    )
    parser.add_argument(
        "--include-dir",
        type=Path,
        action="append",
        default=[],
        help="Dodatkowy katalog include Pawn (można podać wielokrotnie)",
    )
    parser.add_argument(
        "--bot-scripts-dir",
        type=Path,
        default=None,
        help="Jeśli podano, zapisze wygenerowane scenariusze botów w katalogu",
    )
    parser.add_argument(
        "--run-bot-tests",
        action="store_true",
        help="Po wygenerowaniu gamemode uruchom scenariusze botów przeciwko serwerowi",
    )
    parser.add_argument(
        "--gta-dir",
        type=Path,
        default=None,
        help="Katalog instalacji GTA:SA/SA-MP używany przez klienta bota",
    )
    parser.add_argument(
        "--wine-binary",
        type=str,
        default="wine",
        help="Binarna nazwa polecenia Wine uruchamiającego klienta (domyślnie wine)",
    )
    parser.add_argument(
        "--xdotool-binary",
        type=str,
        default="xdotool",
        help="Polecenie xdotool używane do fokusu okna klienta",
    )
    parser.add_argument(
        "--bot-focus-window",
        action="store_true",
        help="Aktywuj okno SA-MP zanim rozpoczniesz wykonywanie skryptu",
    )
    parser.add_argument(
        "--bot-window-title",
        type=str,
        default=None,
        help="Niestandardowy tytuł okna SA-MP wyszukiwany przez xdotool",
    )
    parser.add_argument(
        "--bot-command-file",
        type=Path,
        default=None,
        help="Ścieżka do pliku komend przekazywanych do klienta (opcjonalnie)",
    )
    parser.add_argument(
        "--bot-dry-run",
        action="store_true",
        help="Nie uruchamiaj rzeczywistego klienta SA-MP, tylko zapisuj komendy do pliku",
    )
    parser.add_argument(
        "--bot-record-playback-dir",
        type=Path,
        default=None,
        help="Jeśli ustawiono, zapisuje logi odtworzenia botów w katalogu",
    )
    parser.add_argument(
        "--bot-server-log-dir",
        type=Path,
        default=None,
        help="Domyślny katalog eksportu logów serwera z przebiegów botów",
    )
    parser.add_argument(
        "--bot-client-log-dir",
        type=Path,
        default=None,
        help="Domyślny katalog eksportu logów klienckich",
    )
    parser.add_argument(
        "--bot-only",
        action="append",
        default=[],
        help="Uruchom jedynie scenariusze z podaną nazwą lub tagiem (można powtarzać)",
    )
    parser.add_argument(
        "--bot-skip",
        action="append",
        default=[],
        help="Pomiń scenariusze zawierające nazwę lub tag podany jako argument",
    )
    parser.add_argument(
        "--bot-var",
        action="append",
        default=[],
        help="Nadpisz zmienną scenariusza (format NAZWA=WARTOŚĆ, można powtarzać)",
    )
    parser.add_argument(
        "--bot-retries",
        type=int,
        default=None,
        help="Domyślna liczba ponowień scenariusza przy niepowodzeniu",
    )
    parser.add_argument(
        "--bot-grace-period",
        type=float,
        default=None,
        help="Domyślny czas (w sekundach) oczekiwania przed ponowną próbą",
    )
    parser.add_argument(
        "--bot-fail-fast",
        action="store_true",
        help="Zatrzymaj suite po pierwszym błędzie scenariusza",
    )
    parser.add_argument(
        "--bot-report-json",
        type=Path,
        default=None,
        help="Zapisz raport przebiegów botów do pliku JSON",
    )
    return parser.parse_args(argv)


def _resolve_command_path(
    definition: BotClientDefinition,
    package_dir: Path,
    fallback: Path | None,
) -> Path:
    if definition.command_file:
        path = Path(definition.command_file)
    elif fallback is not None:
        path = fallback
    else:
        path = package_dir / "Test" / f"{definition.name}_commands.log"
    if not path.is_absolute():
        path = package_dir / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _build_client(
    definition: BotClientDefinition,
    package_dir: Path,
    args: argparse.Namespace,
) -> DummyBotClient | WineSampClient:
    command_path = _resolve_command_path(definition, package_dir, args.bot_command_file)
    if definition.type.lower() == "wine":
        gta_dir_value = definition.gta_directory or (args.gta_dir and str(args.gta_dir))
        if gta_dir_value is None:
            raise ValueError(
                f"Definicja klienta {definition.name} wymaga pola 'gta_dir' lub parametru --gta-dir"
            )
        gta_dir = Path(gta_dir_value)
        if not gta_dir.is_absolute():
            gta_dir = package_dir / gta_dir
        gta_dir.mkdir(parents=True, exist_ok=True)
        launcher = definition.launcher or "samp.exe"
        wine_binary = definition.wine_binary or args.wine_binary
        focus_window = definition.focus_window or args.bot_focus_window
        window_title = definition.window_title or args.bot_window_title or "San Andreas Multiplayer"
        xdotool_binary = definition.xdotool_binary or args.xdotool_binary
        log_files: list[tuple[str, Path, str]] = []
        for log_definition in definition.logs:
            log_path = Path(log_definition.path)
            if not log_path.is_absolute():
                log_path = package_dir / log_path
            log_files.append((log_definition.name, log_path, log_definition.encoding))
        chatlog_path = None
        if definition.chatlog:
            chatlog_path = Path(definition.chatlog)
            if not chatlog_path.is_absolute():
                chatlog_path = package_dir / chatlog_path
        return WineSampClient(
            name=definition.name,
            gta_directory=gta_dir,
            launcher=launcher,
            wine_binary=wine_binary,
            command_file=command_path,
            dry_run=definition.dry_run or args.bot_dry_run,
            extra_env={**definition.environment},
            connect_delay=definition.connect_delay,
            reset_commands_on_connect=definition.reset_commands_on_connect,
            focus_window=focus_window,
            window_title=window_title,
            xdotool_binary=xdotool_binary,
            log_files=tuple(log_files),
            chatlog_path=chatlog_path,
            chatlog_encoding=definition.chatlog_encoding or "utf-8",
            setup_actions=definition.setup_actions,
            teardown_actions=definition.teardown_actions,
        )

    if definition.type.lower() == "buffer":
        transport = BufferedCommandTransport()
        return DummyBotClient(
            name=definition.name,
            transport=transport,
            connect_delay=definition.connect_delay,
        )

    separator = definition.command_separator or "\n"
    transport = FileCommandTransport(command_path, separator=separator)
    return DummyBotClient(
        name=definition.name,
        transport=transport,
        connect_delay=definition.connect_delay,
    )


def _fallback_client(args: argparse.Namespace, package_dir: Path) -> DummyBotClient | WineSampClient:
    if args.gta_dir is not None:
        return WineSampClient(
            name="bot-1",
            gta_directory=args.gta_dir,
            wine_binary=args.wine_binary,
            command_file=args.bot_command_file,
            dry_run=args.bot_dry_run,
            focus_window=args.bot_focus_window,
            window_title=args.bot_window_title or "San Andreas Multiplayer",
            xdotool_binary=args.xdotool_binary,
        )
    command_file = args.bot_command_file or package_dir / "Test" / "bot_commands.log"
    transport = FileCommandTransport(command_file)
    return DummyBotClient(name="bot-1", transport=transport)


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)
    config_data = json.loads(args.config.read_text(encoding="utf-8"))
    config = GamemodeConfig.from_dict(config_data)

    variable_overrides: dict[str, object] = {}
    for raw in args.bot_var or []:
        if not raw:
            continue
        key, sep, value = str(raw).partition("=")
        key = key.strip()
        if not key:
            continue
        variable_overrides[key] = value.strip() if sep else "true"
    effective_variables = dict(config.bot_variables)
    effective_variables.update(variable_overrides)

    generator = GamemodeGenerator(template_dir=args.template_dir)

    if args.package_dir is not None:
        package_paths = generator.prepare_package(config, args.package_dir)
        generated_path = package_paths["pawn"]
        print(f"Przygotowano paczkę serwerową w {args.package_dir}")
        print(f" - gamemode: {package_paths['pawn']}")
        print(f" - server.cfg: {package_paths['server_cfg']}")
        print(f" - metadata: {package_paths['metadata']}")
    else:
        generated_path = generator.generate(config, args.output_dir)
        print(f"Wygenerowano gamemode: {generated_path}")

    if args.compile:
        include_dirs = list(args.include_dir or [])
        default_include = Path("inc")
        if default_include.exists() and default_include not in include_dirs:
            include_dirs.append(default_include)
        amx_path = generator.compile(
            generated_path, include_dirs=include_dirs, compiler=args.pawn_compiler
        )
        print(f"Skompilowano gamemode do: {amx_path}")

    if args.bot_scripts_dir is not None:
        bot_paths = config.write_bot_scripts(
            args.bot_scripts_dir, variable_overrides=effective_variables
        )
        if bot_paths:
            print("Zapisano scenariusze botów:")
            for path in bot_paths:
                print(f" - {path}")
        else:
            print("Brak scenariuszy botów do zapisania")

    if args.run_bot_tests:
        package_dir = args.package_dir or args.output_dir
        if not package_dir.exists():
            raise FileNotFoundError(
                "Do uruchomienia testów botów wymagany jest katalog paczki serwerowej"
            )
        plan = config.bot_automation_plan()
        plan_contexts = (
            plan.contexts(
                config.scenarios,
                macros=config.bot_macros,
                global_variables=effective_variables,
            )
            if plan
            else []
        )
        scripts = config.bot_scripts(variable_overrides=effective_variables)
        if not plan_contexts and not scripts:
            print("Brak scenariuszy botów do uruchomienia")
        else:
            server_controller = SampServerController(package_dir)
            if plan and plan.clients:
                clients = [_build_client(defn, package_dir, args) for defn in plan.clients]
            else:
                clients = [_fallback_client(args, package_dir)]
            orchestrator = TestOrchestrator(
                clients=clients,
                scripts_dir=Path("tests/generated_scripts"),
                server_controller=server_controller,
            )
            contexts: list[BotRunContext]
            if plan_contexts:
                contexts = plan_contexts
            else:
                contexts = [BotRunContext(script=script) for script in scripts]
            include_filters = {value.strip().lower() for value in args.bot_only or [] if value}
            exclude_filters = {value.strip().lower() for value in args.bot_skip or [] if value}

            def _context_tokens(context: BotRunContext) -> set[str]:
                desc = (context.script.description or "").strip()
                tokens: set[str] = set()
                if desc:
                    lowered = desc.lower()
                    tokens.add(lowered)
                    tokens.add(slugify_description(desc))
                tokens.update(tag.lower() for tag in context.tags)
                return {token for token in tokens if token}

            if include_filters:
                contexts = [
                    context for context in contexts if _context_tokens(context) & include_filters
                ]
            if exclude_filters:
                contexts = [
                    context for context in contexts if not (_context_tokens(context) & exclude_filters)
                ]
            if args.bot_retries is not None:
                for context in contexts:
                    context.max_retries = max(context.max_retries, args.bot_retries)
            if args.bot_grace_period is not None:
                for context in contexts:
                    if context.grace_period <= 0:
                        context.grace_period = args.bot_grace_period
            if args.bot_fail_fast:
                for context in contexts:
                    context.fail_fast = True
            if not contexts:
                print("Brak scenariuszy botów do uruchomienia po zastosowaniu filtrów")
                return generated_path
            record_root_arg = args.bot_record_playback_dir
            package_root = package_dir
            for context in contexts:
                if (
                    context.record_playback_dir is not None
                    and not context.record_playback_dir.is_absolute()
                ):
                    context.record_playback_dir = package_root / context.record_playback_dir
                if (
                    context.server_log_export is not None
                    and not context.server_log_export.is_absolute()
                ):
                    context.server_log_export = package_root / context.server_log_export
                for export in context.client_log_exports:
                    if export.target_path is not None and not export.target_path.is_absolute():
                        export.target_path = package_root / export.target_path
            if record_root_arg is not None:
                resolved_root = (
                    record_root_arg
                    if record_root_arg.is_absolute()
                    else package_root / record_root_arg
                )
                resolved_root.mkdir(parents=True, exist_ok=True)
                for context in contexts:
                    if context.record_playback_dir is None:
                        context.record_playback_dir = resolved_root
            if args.bot_server_log_dir is not None:
                server_log_root = (
                    args.bot_server_log_dir
                    if args.bot_server_log_dir.is_absolute()
                    else package_root / args.bot_server_log_dir
                )
                server_log_root.mkdir(parents=True, exist_ok=True)
            else:
                server_log_root = None
            if args.bot_client_log_dir is not None:
                client_log_root = (
                    args.bot_client_log_dir
                    if args.bot_client_log_dir.is_absolute()
                    else package_root / args.bot_client_log_dir
                )
                client_log_root.mkdir(parents=True, exist_ok=True)
            else:
                client_log_root = None
            if server_log_root is not None:
                for context in contexts:
                    if context.server_log_export is None:
                        slug = slugify_description(context.script.description)
                        context.server_log_export = server_log_root / f"{slug}_server.log"
            if client_log_root is not None:
                for context in contexts:
                    for export in context.client_log_exports:
                        if export.target_path is None:
                            slug = slugify_description(context.script.description)
                            export.target_path = (
                                client_log_root
                                / f"{slug}_{export.client_name}_{export.log_name}.log"
                            )
            registered: dict[str, Path] = {}
            report_entries: list[dict[str, object]] = []
            for context in contexts:
                desc = context.script.description or "scenario"
                if desc not in registered:
                    registered[desc] = orchestrator.register_script(context.script)
            results = orchestrator.run_suite(contexts)
            for result in results:
                saved_path = registered.get(result.script.description or "scenario")
                desc = result.script.description or "scenario"
                status = result.status_label()
                header = (
                    f"[{status}] {desc} (iteracja {result.iteration_index + 1}, próba {result.attempt_index})"
                )
                if saved_path is not None:
                    header += f" (zapis: {saved_path})"
                print(header)
                if result.duration is not None:
                    print(f"   czas trwania: {result.duration:.2f}s")
                for client_result in result.client_results:
                    if client_result.log is None:
                        print(f" - {client_result.client_name}: brak logu z przebiegu")
                    else:
                        payloads = client_result.log.commands_sent()
                        joined_payloads = ", ".join(payloads)
                        print(
                            f" - {client_result.client_name}: wysłano {len(payloads)} komend ({joined_payloads})"
                        )
                        print(
                            f"   czas skryptu: {client_result.log.total_duration():.2f}s / zdarzeń: {len(client_result.log.events)}"
                        )
                        if client_result.playback_log_path is not None:
                            print(
                                f"   zapis odtworzenia: {client_result.playback_log_path}"
                            )
                        if client_result.screenshots:
                            joined = ", ".join(str(path) for path in client_result.screenshots)
                            print(f"   zrzuty ekranu: {joined}")
                if result.failures:
                    for failure in result.failures:
                        print(
                            f"   ❌ ({failure.category}) {failure.subject}: {failure.message}"
                        )
                elif result.log_expectations or result.client_log_expectations:
                    print("   ✅ wszystkie oczekiwania spełnione")
                if result.assertions:
                    print("   Asercje/metryki:")
                    for assertion in result.assertions:
                        icon = "✅" if assertion.passed else "❌"
                        detail_parts: list[str] = []
                        if assertion.description:
                            detail_parts.append(assertion.description)
                        if assertion.expected:
                            expected_parts = ", ".join(
                                f"{key}={value}" for key, value in assertion.expected.items()
                            )
                            detail_parts.append(f"oczekiwane: {expected_parts}")
                        if assertion.actual is not None:
                            detail_parts.append(f"wartość={assertion.actual}")
                        if assertion.message:
                            detail_parts.append(assertion.message)
                        details = "; ".join(detail_parts)
                        line = f"   {icon} {assertion.name}"
                        if details:
                            line += f": {details}"
                        print(line)
                if result.log_expectations:
                    for expectation in result.log_expectations:
                        base = (
                            f"{expectation.matched_count}/{expectation.required_occurrences}"
                        )
                        expectation_status = "OK" if expectation.matched else "NIE"
                        details: list[str] = [base]
                        if expectation.match_type != "substring":
                            details.append(f"tryb={expectation.match_type}")
                        if not expectation.case_sensitive:
                            details.append("nocase")
                        if expectation.timeout is not None:
                            details.append(f"timeout={expectation.timeout:.1f}s")
                        if expectation.description:
                            details.append(expectation.description)
                        joined_details = ", ".join(details)
                        print(
                            f"   oczekiwanie logu '{expectation.phrase}': {expectation_status} ({joined_details})"
                        )
                if result.server_log_path is not None:
                    print(f"   zapis logu serwera: {result.server_log_path}")
                elif result.server_log_excerpt:
                    preview = " ".join(result.server_log_excerpt.strip().splitlines()[:2])
                    if preview:
                        print(f"   fragment logu serwera: {preview}")
                if result.client_log_exports:
                    for export in result.client_log_exports:
                        label = f"{export.client_name}/{export.log_name}"
                        if export.target_path is not None:
                            print(f"   log klienta {label}: {export.target_path}")
                        elif export.content:
                            lines = len(export.content.splitlines())
                            print(f"   log klienta {label}: {lines} linii (w pamięci)")
                if args.bot_report_json is not None:
                    report_entries.append(
                        {
                            "description": desc,
                            "status": status,
                            "tags": list(result.tags),
                            "attempt": result.attempt_index,
                            "iteration": result.iteration_index,
                            "duration": result.duration,
                            "clients": [
                                {
                                    "name": client_result.client_name,
                                    "has_log": client_result.log is not None,
                                    "playback_log": (
                                        str(client_result.playback_log_path)
                                        if client_result.playback_log_path is not None
                                        else None
                                    ),
                                    "screenshots": [
                                        str(path) for path in client_result.screenshots
                                    ],
                                }
                                for client_result in result.client_results
                            ],
                            "log_expectations": [
                                {
                                    "phrase": expectation.phrase,
                                    "matched": expectation.matched,
                                    "matches": expectation.matched_count,
                                    "required": expectation.required_occurrences,
                                    "match_type": expectation.match_type,
                                    "case_sensitive": expectation.case_sensitive,
                                    "description": expectation.description,
                                    "timeout": expectation.timeout,
                                }
                                for expectation in result.log_expectations
                            ],
                            "client_expectations": [
                                {
                                    "client": expectation.client_name,
                                    "log": expectation.log_name,
                                    "phrase": expectation.phrase,
                                    "matched": expectation.matched,
                                }
                                for expectation in result.client_log_expectations
                            ],
                            "failures": [
                                {
                                    "category": failure.category,
                                    "subject": failure.subject,
                                    "message": failure.message,
                                }
                                for failure in result.failures
                            ],
                            "assertions": [
                                {
                                    "name": assertion.name,
                                    "passed": assertion.passed,
                                    "actual": assertion.actual,
                                    "expected": dict(assertion.expected),
                                    "message": assertion.message,
                                    "description": assertion.description,
                                }
                                for assertion in result.assertions
                            ],
                            "server_log_path": (
                                str(result.server_log_path)
                                if result.server_log_path is not None
                                else None
                            ),
                            "server_log_excerpt": (
                                result.server_log_excerpt
                                if result.server_log_excerpt and result.server_log_path is None
                                else None
                            ),
                            "client_log_exports": [
                                {
                                    "client": export.client_name,
                                    "log": export.log_name,
                                    "path": str(export.target_path)
                                    if export.target_path is not None
                                    else None,
                                    "lines": len(export.content.splitlines())
                                    if export.content
                                    else 0,
                                }
                                for export in result.client_log_exports
                            ],
                        }
                    )
                print("---")

            stats = TestOrchestrator.summarise_results(results)
            scenario_stats = TestOrchestrator.summarise_per_script(results)
            client_stats = TestOrchestrator.summarise_per_client(results)
            tag_stats = TestOrchestrator.summarise_per_tag(results)
            print(
                "Podsumowanie: "
                f"{stats.successful_runs}/{stats.total_runs} scenariuszy zakończonych sukcesem"
            )
            if stats.success_rate is not None:
                print(f"   skuteczność: {stats.success_rate * 100:.1f}%")
            duration_segments: list[str] = []
            if stats.average_duration is not None:
                duration_segments.append(f"średni {stats.average_duration:.2f}s")
            if stats.median_duration is not None:
                duration_segments.append(f"mediana {stats.median_duration:.2f}s")
            if stats.p90_duration is not None:
                duration_segments.append(f"p90 {stats.p90_duration:.2f}s")
            if (
                stats.shortest_duration is not None
                and stats.longest_duration is not None
                and stats.total_runs
            ):
                duration_segments.append(
                    f"zakres {stats.shortest_duration:.2f}s-{stats.longest_duration:.2f}s"
                )
            if duration_segments:
                print(f"   czasy: {', '.join(duration_segments)}")
            if stats.failure_categories:
                details = ", ".join(
                    f"{category}: {count}" for category, count in sorted(stats.failure_categories.items())
                )
                print(f"   kategorie błędów: {details}")
            interesting_scenarios = [
                (description, summary)
                for description, summary in scenario_stats.items()
                if summary.failed_runs or summary.retries
            ]
            if interesting_scenarios:
                print("   szczegóły scenariuszy:")
                for description, summary in interesting_scenarios:
                    print(
                        "      "
                        f"{description}: {summary.successful_runs}/{summary.total_runs} udanych, "
                        f"ostatni wynik {summary.last_status}"
                    )
                    scenario_duration_parts: list[str] = []
                    if summary.average_duration is not None:
                        scenario_duration_parts.append(
                            f"średnio {summary.average_duration:.2f}s"
                        )
                    if summary.median_duration is not None:
                        scenario_duration_parts.append(
                            f"mediana {summary.median_duration:.2f}s"
                        )
                    if summary.p90_duration is not None:
                        scenario_duration_parts.append(f"p90 {summary.p90_duration:.2f}s")
                    if scenario_duration_parts:
                        print("         czasy: " + ", ".join(scenario_duration_parts))
                    if summary.retries:
                        print(
                            "         "
                            f"ponowień: {summary.retries}, sukcesów po ponowieniu: {summary.flaky_successes}"
                        )
                    if summary.failure_categories:
                        scenario_details = ", ".join(
                            f"{category}: {count}"
                            for category, count in sorted(summary.failure_categories.items())
                        )
                        print(f"         błędy: {scenario_details}")

            if client_stats:
                print("   statystyki klientów:")
                for name, summary in client_stats.items():
                    print(
                        "      "
                        f"{name}: {summary.successful_runs}/{summary.total_runs} udanych, "
                        f"ostatni wynik {summary.last_status}"
                    )
                    print(
                        "         "
                        f"logi odtwarzania: {summary.runs_with_logs}/{summary.total_runs}"
                    )
                    if summary.total_commands:
                        average_commands = (
                            f"{summary.average_commands:.1f}"
                            if summary.average_commands is not None
                            else "-"
                        )
                        command_line = (
                            "         "
                            f"komendy: łącznie {summary.total_commands}, średnio {average_commands} na log"
                        )
                        if summary.median_commands is not None:
                            command_line += f", mediana {summary.median_commands:.1f}"
                        print(command_line)
                    if summary.average_log_duration is not None:
                        log_line = (
                            "         "
                            f"czas logu: {summary.total_log_duration:.2f}s łącznie, "
                            f"średnio {summary.average_log_duration:.2f}s"
                        )
                        if summary.median_log_duration is not None:
                            log_line += f", mediana {summary.median_log_duration:.2f}s"
                        print(log_line)
            if tag_stats:
                print("   tagi scenariuszy:")
                for tag, summary in tag_stats.items():
                    print(
                        "      "
                        f"#{tag}: {summary.successful_runs}/{summary.total_runs} udanych, "
                        f"ostatni wynik {summary.last_status}"
                    )
                    tag_duration_parts: list[str] = []
                    if summary.average_duration is not None:
                        tag_duration_parts.append(f"średnio {summary.average_duration:.2f}s")
                    if summary.median_duration is not None:
                        tag_duration_parts.append(f"mediana {summary.median_duration:.2f}s")
                    if summary.p90_duration is not None:
                        tag_duration_parts.append(f"p90 {summary.p90_duration:.2f}s")
                    if tag_duration_parts:
                        print("         czasy: " + ", ".join(tag_duration_parts))
                    if summary.retries:
                        print(
                            "         "
                            f"ponowień: {summary.retries}, sukcesów po ponowieniu: {summary.flaky_successes}"
                        )
                    if summary.failure_categories:
                        tag_failures = ", ".join(
                            f"{category}: {count}"
                            for category, count in sorted(summary.failure_categories.items())
                        )
                        print(f"         błędy: {tag_failures}")
                    if summary.scenario_counts:
                        scenario_overview = ", ".join(
                            f"{scenario}: {count}"
                            for scenario, count in summary.scenario_counts.items()
                        )
                        print(f"         scenariusze: {scenario_overview}")

            if args.bot_report_json is not None:
                report_path = args.bot_report_json
                if not report_path.is_absolute():
                    report_path = package_root / report_path
                report_path.parent.mkdir(parents=True, exist_ok=True)
                summary = stats.as_dict()
                summary["per_scenario"] = {
                    description: scenario.as_dict()
                    for description, scenario in scenario_stats.items()
                }
                summary["per_client"] = {
                    name: client.as_dict() for name, client in client_stats.items()
                }
                summary["per_tag"] = {tag: tag_summary.as_dict() for tag, tag_summary in tag_stats.items()}
                payload = {
                    "generated_gamemode": str(generated_path),
                    "package_dir": str(package_dir),
                    "variables": {key: str(value) for key, value in effective_variables.items()},
                    "results": report_entries,
                    "summary": summary,
                }
                report_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"Zapisano raport przebiegów botów: {report_path}")

    return generated_path


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
