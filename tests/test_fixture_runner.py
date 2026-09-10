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
