"""Command line interface for AutoRP utilities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bots import BufferedCommandTransport, DummyBotClient, FileCommandTransport, WineSampClient
from .config import BotClientDefinition, GamemodeConfig
from .generator import GamemodeGenerator
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
        bot_paths = config.write_bot_scripts(args.bot_scripts_dir)
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
        plan_contexts = plan.contexts(config.scenarios) if plan else []
        scripts = config.bot_scripts()
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
            def _slugify(text: str) -> str:
                normalised = (text or "scenario").strip().lower()
                if not normalised:
                    normalised = "scenario"
                safe = [
                    char if char.isalnum() or char in {"-", "_"} else "_"
                    for char in normalised
                ]
                slug = "".join(safe)
                return slug or "scenario"
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
                        slug = _slugify(context.script.description or "scenario")
                        context.server_log_export = server_log_root / f"{slug}_server.log"
            if client_log_root is not None:
                for context in contexts:
                    for export in context.client_log_exports:
                        if export.target_path is None:
                            slug = _slugify(context.script.description or "scenario")
                            export.target_path = (
                                client_log_root
                                / f"{slug}_{export.client_name}_{export.log_name}.log"
                            )
            registered: dict[str, Path] = {}
            for context in contexts:
                desc = context.script.description or "scenario"
                if desc not in registered:
                    registered[desc] = orchestrator.register_script(context.script)
            results = orchestrator.run_suite(contexts)
            for result in results:
                saved_path = registered.get(result.script.description or "scenario")
                header = f"Uruchomiono scenariusz {result.script.description}"
                if saved_path is not None:
                    header += f" (zapis: {saved_path})"
                print(header)
                for client_result in result.client_results:
                    if client_result.log is None:
                        print(f" - {client_result.client_name}: brak logu z przebiegu")
                    else:
                        payloads = client_result.log.commands_sent()
                        print(
                            f" - {client_result.client_name}: wysłano {len(payloads)} komend ({', '.join(payloads)})"
                        )
                        if client_result.playback_log_path is not None:
                            print(
                                f"   zapis odtworzenia: {client_result.playback_log_path}"
                            )
                        if client_result.screenshots:
                            joined = ", ".join(str(path) for path in client_result.screenshots)
                            print(f"   zrzuty ekranu: {joined}")
                if result.log_expectations:
                    for expectation in result.log_expectations:
                        status = "OK" if expectation.matched else "NIE ZNALEZIONO"
                        print(f"   oczekiwanie logu '{expectation.phrase}': {status}")
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
                print("---")

    return generated_path


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
