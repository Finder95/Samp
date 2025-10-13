"""Gamemode generation utilities."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Mapping, Sequence
from string import Template
from .config import GamemodeConfig


class TemplateRenderer:
    """Simple template renderer based on :class:`string.Template`."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template {self.template_path} does not exist")

    def render(self, context: Mapping[str, object]) -> str:
        raw_template = self.template_path.read_text(encoding="utf-8")
        templated = Template(raw_template)
        # Convert lists into formatted strings expected by Pawn.
        safe_context = {
            key: "\n".join(value) if isinstance(value, list) else value
            for key, value in context.items()
        }
        return templated.safe_substitute(safe_context)


class GamemodeGenerator:
    """Generate Pawn gamemode files based on :class:`GamemodeConfig`."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path(__file__).with_suffix("").parent / "templates"
        self.template_dir = self.template_dir.resolve()
        self.base_template = TemplateRenderer(self.template_dir / "base_gamemode.pwn.tpl")

    def generate(self, config: GamemodeConfig, output_dir: Path) -> Path:
        """Generate the Pawn file and return the created path."""
        output_dir = config.ensure_output_directory(output_dir)
        pawn_code = self.base_template.render(config.pawn_context())
        target = output_dir / f"{config.name}.pwn"
        target.write_text(pawn_code, encoding="utf-8")
        return target

    def prepare_package(self, config: GamemodeConfig, package_dir: Path) -> dict[str, Path]:
        """Generate a complete SA-MP package with server.cfg and metadata."""

        package_dir.mkdir(parents=True, exist_ok=True)
        gamemodes_dir = package_dir / "gamemodes"
        gamemodes_dir.mkdir(parents=True, exist_ok=True)
        pawn_path = self.generate(config, gamemodes_dir)

        server_cfg_path = package_dir / "server.cfg"
        server_cfg_path.write_text(config.server_cfg_content(), encoding="utf-8")

        metadata_path = package_dir / "autorppackage.json"
        metadata_path.write_text(config.metadata_json(), encoding="utf-8")

        return {
            "pawn": pawn_path,
            "server_cfg": server_cfg_path,
            "metadata": metadata_path,
        }

    def compile(self, pawn_file: Path, include_dirs: Sequence[Path] | None = None, compiler: Path | None = None) -> Path:
        """Compile Pawn source into AMX bytecode using pawncc."""

        compiler_path = Path(compiler) if compiler else shutil.which("pawncc")
        if compiler_path is None:
            raise FileNotFoundError("Nie znaleziono kompilatora pawncc. Zainstaluj go lub podaj ścieżkę przez --pawn-compiler")

        include_dirs = include_dirs or []
        output = pawn_file.with_suffix(".amx")
        command = [str(compiler_path), str(pawn_file), f"-o{output}"]
        for include_dir in include_dirs:
            command.append(f"-i{include_dir}")

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "Kompilacja Pawn zakończyła się niepowodzeniem:\n" + result.stderr
            )
        return output


__all__ = ["GamemodeGenerator"]
