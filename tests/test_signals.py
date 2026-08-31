"""Tests for signal extraction.

The extractor is the swappable layer, but its output contract is load-bearing
for everything downstream, so the contract itself is tested here.
"""

from __future__ import annotations

from secondsignal.signals import extract


def test_extraction_is_deterministic():
    assert extract("I'm blocked on this painting") == extract("I'm blocked on this painting")


def test_regulation_falls_with_dysregulation_markers():
    calm = extract("let's plan out my week")
    spiraling = extract("I'm spiraling and falling apart and can't stop")
    assert spiraling.regulation < calm.regulation
    assert spiraling.is_dysregulated


def test_regulation_is_clamped_to_unit_interval():
    extreme = extract(
        "panic spiraling can't stop falling apart breaking down overwhelmed meltdown"
    )
    assert 0.0 <= extreme.regulation <= 1.0


def test_domains_and_modes_are_detected_independently():
    signals = extract("my grandmother died and I want you to be gentle")
    assert "grief" in signals.domains
    assert "comfort" in signals.modes


def test_every_feature_is_traceable_to_a_token():
    """Auditability requires that no feature appears without its evidence."""
    signals = extract("I have adhd and I'm completely overwhelmed")
    for domain in signals.domains:
        assert signals.evidence[f"domain:{domain}"]
    assert signals.evidence["regulation:down"]


def test_neutral_text_yields_no_domains():
    signals = extract("hello")
    assert not signals.domains
    assert not signals.modes


def test_case_and_whitespace_are_normalized():
    a = extract("MY GRANDMOTHER   DIED")
    b = extract("my grandmother died")
    assert a.domains == b.domains


def test_multiword_phrases_match_across_line_breaks():
    signals = extract("I can't\nbreathe")
    assert "somatic_distress" in signals.domains
