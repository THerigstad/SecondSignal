"""Rulings 1–8: prevent the design record from claiming future work is built."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR26 = ROOT / "docs/adr/0026-twins-two-presentations-one-routing-contract.md"
ADR27 = ROOT / "docs/adr/0027-a-relatives-return-to-use-is-a-hold.md"


class TestOrder1Documentation(unittest.TestCase):
    def setUp(self):
        self.presentation = " ".join(ADR26.read_text(encoding="utf-8").split())
        self.relapse = " ".join(ADR27.read_text(encoding="utf-8").split())

    def test_decision1_names_only_preserves_two_name_veto(self):
        self.assertIn("The plate shows both names without she or he labels", self.presentation)
        self.assertIn("End of discussion, unless something legitimately challenges that.", self.presentation)

    def test_decision2_shuffle_is_ruled_and_future_not_the_live_skip(self):
        self.assertIn("The shuffle is ruled, not built in this push.", self.presentation)
        self.assertIn("four she presentations and three he presentations", self.presentation)
        self.assertIn("Today's demo still uses as written when the door is skipped.", self.presentation)
        self.assertIn("The operator proposed the random choice", self.presentation)  # "the operator" in prose; the name stays on the byline (house rule; integration of 4 October 2026)
        self.assertIn("onboarding information never chooses a presentation", self.presentation)

    def test_decision3_neither_is_not_called_a_completed_neutral_design(self):
        self.assertIn("Today's neither is not a neutral presentation.", self.presentation)
        self.assertIn("the supplied front pages contain no canon block", self.presentation)
        self.assertIn("there is no separate both answer", self.presentation)
        self.assertNotIn("which is the form the front page's canon block writes", self.presentation)

    def test_decision4_exact_door_copy_and_house_only_reoffer(self):
        self.assertIn("This describes the characters, not you. For now, your choice lasts for this visit. We're building it so your characters stay the way you set them, and so you can shape them to fit what you need.", self.presentation)
        self.assertIn("only as a plain message from SecondSignal itself, never from a character", self.presentation)

    def test_decision5_survivor_contract_is_hard_personal_and_still_open(self):
        for phrase in (
            "no neutral or ambiguous fallback", "per person, never per deployment",
            "every future roster member", "every voice once voices arrive",
            "same reply", "ask-once-with-cooldown", "next calm moment",
            "r3-survivor-women-only-001", "r3-0026-survivor-offer-001",
            "The survivor case stays open until decision 10's character write-ups are fixed",
        ):
            self.assertIn(phrase, self.presentation)

    def test_decision6_cody_rule_and_disputes_remain_visible(self):
        self.assertIn("anytime there's a relapse, it should have Cody as a sidekick, if not seat him.", self.relapse)
        self.assertIn("gpt-d3-third-person", self.relapse)
        self.assertIn("qwn-d3-thirdperson-relapse-001", self.relapse)
        self.assertIn("The crisis card comes first and nobody takes a seat.", self.relapse)

    def test_decision7_uncertain_subject_holds_and_gaps_are_not_fixes(self):
        for phrase in (
            "A self mention anywhere, including first-person plural", "fails toward someone else's",
            "A bare report", "An ask", "Qwen's second, independent subject detector",
            "strict expected failures", "I have to reset my date", "twins-sponsor-case-001",
        ):
            self.assertIn(phrase, self.relapse)

    def test_decision8_message_does_not_freeze_safety_state(self):
        self.assertIn("The correct invariant is that a message never directly changes the presentation preference. Safety evaluation and other authorized policy-state transitions still occur.", self.presentation)
        self.assertNotIn("yields `ask_first` and an unchanged session", self.presentation)
        self.assertNotIn("(`ask_first`, and nothing else)", self.presentation)


if __name__ == "__main__":
    unittest.main()
