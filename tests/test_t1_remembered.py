"""Optional order T1 version: remembered presentation stays apart from keys."""

from __future__ import annotations

import json

import pytest

from apps.talking_table import server


@pytest.mark.parametrize("remember", [False, True])
def test_t1_presentation_restarts_only_when_remembered_without_any_key(tmp_path, remember):
    """A confirmed presentation and name choice survive restart only when Remember is on."""
    app = server.TableApp(data_dir=tmp_path / "remembered-presentation")
    restored = None
    try:
        app.update_settings({"remember": remember, "presentation": "neither",
                             "chosen_names": {"willow": "Will"}})
        restored = server.TableApp(data_dir=app.data_dir)
        assert restored.settings["presentation"] == ("neither" if remember else "as_written")
        assert restored.settings["chosen_names"] == ({"willow": "Will"} if remember else {})
        assert restored.key == restored.voice_key == restored.lights_key == ""
        if remember:
            settings = json.loads(app.settings_path.read_text(encoding="utf-8"))
            preferences = json.loads(app.preferences_path.read_text(encoding="utf-8"))
            assert not any("blob" in name for name in settings)
            assert "presentation" not in settings["settings"]
            assert "chosen_names" not in settings["settings"]
            assert preferences["presentation"] == "neither"
            assert preferences["chosen_names"] == {"willow": "Will"}
            assert not any("key" in name for name in preferences)
    finally:
        app.close()
        if restored is not None:
            restored.close()


def test_t1_forgetting_removes_presentation_while_retaining_live_choice(tmp_path):
    """Turning Remember off deletes the saved choice but does not reset the current session."""
    app = server.TableApp(data_dir=tmp_path / "forget-presentation")
    restored = None
    try:
        app.update_settings({"remember": True, "presentation": "women"})
        session = app.harness.session
        app.update_settings({"remember": False})
        assert app.settings["presentation"] == "women" and app.harness.session is session
        assert not app.preferences_path.exists()
        restored = server.TableApp(data_dir=app.data_dir)
        assert restored.settings["presentation"] == "as_written"
    finally:
        app.close()
        if restored is not None:
            restored.close()


def test_t1_voice_remember_alone_does_not_remember_presentation(tmp_path, monkeypatch):
    """Remembering a voice key alone never opts into remembering character presentation."""
    monkeypatch.setattr(server, "_secret_blob", lambda value, **kwargs: bytes(byte ^ 0xA5 for byte in value))
    app = server.TableApp(data_dir=tmp_path / "voice-only")
    restored = None
    try:
        app.update_settings({"voice_key": "test-remembered-voice-secret-not-real", "voice_remember": True,
                             "presentation": "men"})
        assert not app.preferences_path.exists()
        restored = server.TableApp(data_dir=app.data_dir)
        assert restored.settings["presentation"] == "as_written"
        assert restored.voice_key and restored.settings["voice_remember"]
    finally:
        app.close()
        if restored is not None:
            restored.close()
