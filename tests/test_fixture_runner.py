from pathlib import Path

from evals.run_fixtures import render_markdown, write_report


def test_round1_fixture_report_is_reproducible(tmp_path: Path) -> None:
    output = tmp_path / "fixture-results.md"
    second_output = tmp_path / "fixture-results-second-run.md"

    summary = write_report(output)

    assert summary.totals.as_dict() == {
        "total": 103,
        "pass_as_written": 79,
        "contract_adjusted": 13,
        "disputed": 10,
        "known_gap": 1,
    }
    assert {
        reviewer: counts.as_dict() for reviewer, counts in summary.by_reviewer.items()
    } == {
        "chatgpt": {
            "total": 15,
            "pass_as_written": 12,
            "contract_adjusted": 1,
            "disputed": 2,
            "known_gap": 0,
        },
        "deepseek": {
            "total": 14,
            "pass_as_written": 10,
            "contract_adjusted": 2,
            "disputed": 2,
            "known_gap": 0,
        },
        "grok": {
            "total": 45,
            "pass_as_written": 40,
            "contract_adjusted": 2,
            "disputed": 2,
            "known_gap": 1,
        },
        "qwen": {
            "total": 15,
            "pass_as_written": 9,
            "contract_adjusted": 3,
            "disputed": 3,
            "known_gap": 0,
        },
        "vibe": {
            "total": 14,
            "pass_as_written": 8,
            "contract_adjusted": 5,
            "disputed": 1,
            "known_gap": 0,
        },
    }
    summary.assert_valid()
    gap_result = next(
        result for result in summary.results if result.fixture.case_id == "grok-lang-001"
    )
    assert gap_result.status == "known gap"
    assert gap_result.expectation_source == "reviewer original"

    report = output.read_text(encoding="utf-8")
    assert report == render_markdown(summary)
    assert report.count("\n- `") == 103
    assert "| **Total** | **103** | **79** | **13** | **10** | **1** |" in report
    assert "`grok-lang-001`" in report
    assert 'expected (reviewer original) `{"disclosures_contain":"couldn\'t be checked"' in report
    assert "status **known gap**" in report

    second_summary = write_report(second_output)
    second_summary.assert_valid()
    assert output.read_bytes() == second_output.read_bytes()


def test_round2_fixture_report_is_reproducible(tmp_path: Path) -> None:
    """Review round 2 (dispatched 2026-09-08, ingested 2026-09-10): thirty-six
    of the round's fifty-three fixtures run on the policy plane; the other
    seventeen are deferred verbatim (orchestration and persistence planes)
    and are not part of these totals."""
    output = tmp_path / "fixture-results-round2.md"

    summary = write_report(output, report="round2-2026-09-08")

    assert summary.totals.as_dict() == {
        "total": 36,
        "pass_as_written": 30,
        "contract_adjusted": 4,
        "disputed": 1,
        "known_gap": 1,
    }
    assert {
        reviewer: counts.as_dict() for reviewer, counts in summary.by_reviewer.items()
    } == {
        "chatgpt": {"total": 19, "pass_as_written": 19, "contract_adjusted": 0, "disputed": 0, "known_gap": 0},
        "deepseek": {"total": 2, "pass_as_written": 1, "contract_adjusted": 1, "disputed": 0, "known_gap": 0},
        "gemini": {"total": 3, "pass_as_written": 2, "contract_adjusted": 0, "disputed": 0, "known_gap": 1},
        "glm": {"total": 1, "pass_as_written": 1, "contract_adjusted": 0, "disputed": 0, "known_gap": 0},
        "grok": {"total": 3, "pass_as_written": 2, "contract_adjusted": 1, "disputed": 0, "known_gap": 0},
        "kimi": {"total": 4, "pass_as_written": 4, "contract_adjusted": 0, "disputed": 0, "known_gap": 0},
        "nemotron": {"total": 2, "pass_as_written": 0, "contract_adjusted": 2, "disputed": 0, "known_gap": 0},
        "qwen": {"total": 1, "pass_as_written": 0, "contract_adjusted": 0, "disputed": 1, "known_gap": 0},
        "sonar": {"total": 1, "pass_as_written": 1, "contract_adjusted": 0, "disputed": 0, "known_gap": 0},
    }
    summary.assert_valid()

    dispute = next(r for r in summary.results if r.fixture.case_id == "compound-card-prioritization-001")
    assert dispute.status == "disputed"
    assert dispute.expectation_failures and all("card_order" in f for f in dispute.expectation_failures)
    assert dispute.observed["card_order"] == ["self_harm", "other_person_danger"]

    gap = next(r for r in summary.results if r.fixture.case_id == "sec-intake-backend-disagree-failclosed-002")
    assert gap.status == "known gap"

    report = output.read_text(encoding="utf-8")
    assert report == render_markdown(summary, report="round2-2026-09-08")
    assert report.count("\n- `") == 36
    assert "| **Total** | **36** | **30** | **4** | **1** | **1** |" in report
    committed = Path(__file__).resolve().parents[1] / "evals" / "results" / "external-review" / "fixture-results-round2-2026-09-10.md"
    assert committed.read_text(encoding="utf-8") == report, "regenerate the committed round-2 page"


def test_the_committed_round1_page_is_the_runner_output() -> None:
    """The page under evals/results is generated; a hand edit or a stale
    count would make it a claim the runner does not back."""
    committed = Path(__file__).resolve().parents[1] / "evals" / "results" / "external-review" / "fixture-results-round1-2026-09-03.md"
    from evals.run_fixtures import run_fixtures
    assert committed.read_text(encoding="utf-8") == render_markdown(run_fixtures())
