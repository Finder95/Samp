import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.autorp.cli import main


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generator_creates_file(tmp_path: Path, monkeypatch):
    config_path = Path("configs/sample_config.json")
    output_dir = tmp_path / "output"

    def fake_print(*args, **kwargs):  # pragma: no cover - silence prints
        return None

    monkeypatch.setattr("builtins.print", fake_print)
    generated_path = main([str(config_path), "--output-dir", str(output_dir)])

    assert generated_path.exists()
    content = generated_path.read_text(encoding="utf-8")
    assert "AutoRP" in content
    assert "Policja" in content
    assert "GivePlayerMoney(playerid, 500);" in content
    assert "SendRconCommand(\"hostname AutoRP Development\");" in content
    assert "PlayerJob[MAX_PLAYERS]" in content
    assert "SetupEconomy" in content
    assert "HandleJobPaycheck" in content
    assert "PROPERTY_KOMISARIAT_DOWNTOWN" in content
    assert "/kup_komisariat" in content
    assert "CreateActor(280" in content
    assert "HandleScheduledEvent_PAYDAY" in content


def test_cli_prepares_server_package(tmp_path: Path, monkeypatch):
    config_path = Path("configs/sample_config.json")
    package_dir = tmp_path / "server"

    def fake_print(*args, **kwargs):  # pragma: no cover - silence prints
        return None

    monkeypatch.setattr("builtins.print", fake_print)
    pawn_path = main([str(config_path), "--package-dir", str(package_dir)])

    gamemode_path = package_dir / "gamemodes" / pawn_path.name
    assert gamemode_path == pawn_path
    assert gamemode_path.exists()

    server_cfg = (package_dir / "server.cfg").read_text(encoding="utf-8")
    assert "hostname AutoRP Development" in server_cfg
    assert "gamemode0 AutoRP 1" in server_cfg

    metadata = read_json(package_dir / "autorppackage.json")
    assert metadata["name"] == "AutoRP"
    assert "/sluzba" in metadata["commands"]
    assert "Policjant" in metadata["jobs"]
    assert "Apteczka" in metadata["items"]
    assert "Komisariat Downtown" in metadata["properties"]
    assert "Oficer Kowalski" in metadata["npcs"]
    assert "payday" in metadata["events"]

    pawn_content = gamemode_path.read_text(encoding="utf-8")
    assert "AddStaticVehicleEx(596" in pawn_content
    assert 'SendClientMessage(playerid, 0xAA3333FF, "Brak dostępu do tej komendy.");' in pawn_content
    assert 'SetTimerEx("HandleJobPaycheck", floatround(gEconomy[EconomyInterval])' in pawn_content
    assert "CreatePickup(1240" in pawn_content
    assert "gPropertyPickups" in pawn_content
    assert "SendClientMessageToAll(0x33AA33FF, \"[Event] Automatyczny bonus służbowy został wypłacony.\");" in pawn_content
    assert "SetTimer(\"HandleScheduledEvent_PAYDAY\"" in pawn_content


def test_cli_exports_bot_scripts(tmp_path: Path, monkeypatch):
    config_path = Path("configs/sample_config.json")
    scripts_dir = tmp_path / "bots"

    def fake_print(*args, **kwargs):  # pragma: no cover - silence prints
        return None

    monkeypatch.setattr("builtins.print", fake_print)
    main([
        str(config_path),
        "--output-dir",
        str(tmp_path / "out"),
        "--bot-scripts-dir",
        str(scripts_dir),
    ])

    files = list(scripts_dir.glob("*.json"))
    assert files, "expected at least one bot script"
    data = read_json(files[0])
    assert "commands" in data
    assert any(cmd.startswith("/dolacz") for cmd in data["commands"]) 
