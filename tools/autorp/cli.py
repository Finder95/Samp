"""Command line interface for AutoRP utilities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import GamemodeConfig
from .generator import GamemodeGenerator


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

    return generated_path


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
