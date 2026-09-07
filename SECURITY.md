# Security policy

## Report safety regressions privately

Report a crisis-screen bypass or other safety regression privately before
opening a public issue. The reporting contact is:

see the repository owner's GitHub profile

Do not include a real person's message, name, location, account data, or other
identifying detail. Replace it with a synthetic case that reproduces the same
policy behavior.

## What counts as a safety issue

A safety issue is behavior that weakens the policy envelope. Examples include:

- a message that should produce `HUMAN_ESCALATION` instead proceeding to a
  persona;
- normalization, masking, or language handling turning a crisis `HIT` or
  `INCONCLUSIVE` read into a `MISS`;
- a bypass of a boundary, contraindication, careful-side latch, register cap,
  or integrity hold; or
- a required crisis card, disclosure, resource line, or preemption being
  suppressed or softened.

A normal bug does not change the safety decision or envelope. Documentation
errors, installation failures, formatting defects, and a wrong ranking between
otherwise eligible personas are normally public bugs. If the distinction is
unclear, use the private reporting path.

## What a report must contain

Every report must include a sanitized, synthetic fixture in the project's
contract. Follow the schema in `evals/README.md` and include the message,
permitted session fields, expected safety action and outcome, observed result,
and a `why` line. State the affected version or commit and the smallest steps
needed to reproduce the result. A live or identifying message is not an
acceptable fixture.

Maintainers intend to acknowledge a report within three business days and to
provide an initial assessment or request for more information within seven
business days. These are response targets that express intent, not guarantees;
complexity and maintainer availability may change the timing.
