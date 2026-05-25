import os

import server


def test_load_dotenv_file_fills_missing_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("TOTVS_USERNAME=file_user\nTOTVS_PASSWORD=file_pass\n", encoding="utf-8")

    monkeypatch.setenv("TOTVS_ENV_FILE", str(env_file))
    monkeypatch.delenv("TOTVS_USERNAME", raising=False)
    monkeypatch.delenv("TOTVS_PASSWORD", raising=False)
    monkeypatch.delenv("TOTVS_DOTENV_OVERRIDE", raising=False)
    monkeypatch.setattr(server, "_dotenv_loaded", False)

    server._load_dotenv_once()

    assert os.environ["TOTVS_USERNAME"] == "file_user"
    assert os.environ["TOTVS_PASSWORD"] == "file_pass"


def test_load_dotenv_file_can_override_inherited_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("TOTVS_USERNAME=file_user\n", encoding="utf-8")

    monkeypatch.setenv("TOTVS_ENV_FILE", str(env_file))
    monkeypatch.setenv("TOTVS_USERNAME", "old_user")
    monkeypatch.setenv("TOTVS_DOTENV_OVERRIDE", "true")
    monkeypatch.setattr(server, "_dotenv_loaded", False)

    server._load_dotenv_once()

    assert os.environ["TOTVS_USERNAME"] == "file_user"
