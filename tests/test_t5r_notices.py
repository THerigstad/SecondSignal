"""Order T5R: exact Table notices in the policy session's declared language."""

import pytest

from apps.talking_table import server, t3

ENGLISH = {
    "sitting_ended": (
        "It's been a while. After eight quiet hours, that conversation ended on its own. "
        "Welcome back. We're starting a new one."
    ),
    "latch_carried": (
        "This Table is taking extra care because of an earlier conversation on this computer. "
        "That's something the operator can clear with a reason."
    ),
}
SPANISH = {
    "sitting_ended": (
        "Ha pasado un buen rato. Después de ocho horas de silencio, esa conversación terminó "
        "por sí sola. Qué bueno tenerte de vuelta. Empezamos una nueva."
    ),
    "latch_carried": (
        "Esta Mesa está teniendo cuidado extra por una conversación anterior en esta computadora. "
        "Eso es algo que el operador puede levantar con un motivo."
    ),
}


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(tmp_path / "t5r-data")
    try:
        yield instance
    finally:
        instance.close()


def test_the_english_notices_are_exactly_the_operators_words():
    assert t3.T4_LINES == ENGLISH


def test_the_spanish_notices_are_exactly_the_ordered_translation():
    assert t3.T4_LINES_ES == SPANISH


def test_the_spanish_review_state_and_notice_keys_are_explicit():
    assert t3.T4_LINES.keys() == t3.T4_LINES_ES.keys()
    assert "not yet reviewed by a native speaker" in t3.T4_LINES_ES_REVIEW
    assert t3.T4_LINES_ES_REVIEW == (
        "Spanish written by the project manager on 13 October 2026 and not yet reviewed by a native "
        "speaker; it ships because the English is the operator's words and a person who declared "
        "Spanish must not be shown English here; the native review replaces it."
    )


@pytest.mark.parametrize("language,expected", [
    (None, ENGLISH), ("", ENGLISH), ("en-GB", ENGLISH), ("fr", ENGLISH),
    ("es", SPANISH), ("es-419", SPANISH), ("ES-mx", SPANISH),
])
@pytest.mark.parametrize("key", ["sitting_ended", "latch_carried"])
def test_the_notice_language_uses_the_first_lowercase_language_part(language, expected, key):
    assert t3.t4_line(key, language) == expected[key]


@pytest.mark.parametrize("language,expected", [(None, ENGLISH), ("es-419", SPANISH)])
def test_quiet_expiry_uses_the_ending_sessions_declared_language(app, monkeypatch, language, expected):
    now = [1000000.0]
    monkeypatch.setattr(server.time, "time", lambda: now[0])
    app.turn("Help me make a plan for my work tomorrow.")
    app.harness.session.declared_language = language
    original_session = app.session_id
    now[0] = app.last_turn_at + server.SITTING_QUIET_LIMIT_SECONDS
    app.end_quiet_sitting()
    assert app.session_id != original_session
    assert app.sitting(computer=False)["sitting_notice"] is None
    first = app.sitting(computer=True)
    assert first["sitting_notice"] == expected["sitting_ended"]
    assert app.sitting(computer=True)["sitting_notice"] is None


@pytest.mark.parametrize("language,expected", [(None, ENGLISH), ("es-419", SPANISH)])
def test_carried_latch_uses_the_current_sessions_declared_language(app, language, expected):
    app.turn("I am 14 and need help with homework.")
    app.reset()
    app.harness.session.declared_language = language
    phone = app.sitting(computer=False)
    assert phone["latch_carried"] is False and phone["latch_carried_notice"] is None
    first = app.sitting(computer=True)
    assert first["latch_carried"] is True
    assert first["latch_carried_notice"] == expected["latch_carried"]
    again = app.sitting(computer=True)
    assert again["latch_carried"] is False and again["latch_carried_notice"] is None
