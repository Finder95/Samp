"""Command line interface for AutoRP utilities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bots import DummyBotClient, FileCommandTransport, WineSampClient
from .config import GamemodeConfig
from .generator import GamemodeGenerator
from .tester import SampServerController, TestOrchestrator


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
    return parser.parse_args(argv)


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
        scripts = config.bot_scripts()
        if not scripts:
            print("Brak scenariuszy botów do uruchomienia")
        else:
            package_dir = args.package_dir or args.output_dir
            if not package_dir.exists():
                raise FileNotFoundError(
                    "Do uruchomienia testów botów wymagany jest katalog paczki serwerowej"
                )
            server_controller = SampServerController(package_dir)
            if args.gta_dir is not None:
                client = WineSampClient(
                    name="bot-1",
                    gta_directory=args.gta_dir,
                    wine_binary=args.wine_binary,
                    command_file=args.bot_command_file,
                    dry_run=args.bot_dry_run,
                )
            else:
                command_file = args.bot_command_file or Path("Test/bot_commands.log")
                transport = FileCommandTransport(command_file)
                client = DummyBotClient(name="bot-1", transport=transport)
            orchestrator = TestOrchestrator(
                clients=[client],
                scripts_dir=Path("tests/generated_scripts"),
                server_controller=server_controller,
            )
            for script in scripts:
                saved_path = orchestrator.register_script(script)
                result = orchestrator.run(script)
                print(
                    f"Uruchomiono scenariusz {script.description} (zapis: {saved_path})",
                )
                for client_result in result.client_results:
                    if client_result.log is None:
                        print(f" - {client_result.client_name}: brak logu z przebiegu")
                    else:
                        cmds = ", ".join(client_result.log.commands_sent())
                        print(
                            f" - {client_result.client_name}: wysłano {len(client_result.log.events)} akcji ({cmds})"
                        )

    return generated_path


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
