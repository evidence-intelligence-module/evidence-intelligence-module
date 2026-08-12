"""Per-request record of every evidence input attempted, and what came of it
(tasks.md T0-09).

Two things needed this and neither could be built without it.

**Chain of custody.** Constitution Principle III requires a §65B-admissible
package, and the argument a reviewer or forum actually needs to make is "here
is everything this conclusion rests on, and here is what was tried and did not
work." Before this, that answer was scattered across four tables — a
`considered_not_used` flag, a component `status`, a thermal `pass_available`,
a cross-check `outcome` — and could not be stated in one place. "We looked and
there was nothing" and "we never looked" are different claims about the
evidence, and only one of them is a limitation of the world rather than of the
module.

**The confidence tier.** `specs/002-satellite-evidence-parity/issue/open query -
confidence tier threshold values (FR-004).md` adopts a rule table over exactly
this record rather than a cut point on a float — every rule there ("no valid
post-event pixels ⇒ LOW", "SAR substituted ⇒ at most MEDIUM") is a question
about which inputs were available. That is what makes a tier defensible in a
hearing: "the field was not visible on any post-event pass" is an argument,
"confidence was 0.63" is not."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InputOutcome(Enum):
    """What happened to one attempted evidence input.

    A plain `Enum` rather than the `str, Enum` pairing used by `store/schema.py`
    — nothing here is persisted as a column or compared to a bare string; the
    value is serialised explicitly via `.value` in `as_dict`."""

    USED = "USED"
    """Available and contributed to the package."""

    DEGRADED = "DEGRADED"
    """Available but weaker than intended — a substitute source, a placeholder
    model, partial coverage. Contributed, with a caveat that belongs in the
    package rather than only in a log."""

    UNAVAILABLE = "UNAVAILABLE"
    """Attempted and not obtainable. Distinct from NOT_APPLICABLE: this one
    says the module looked."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    """Never attempted, because it does not apply to this request — a thermal
    signal for a hailstorm claim, say. Not a gap in the evidence."""


@dataclass(frozen=True)
class EvidenceInput:
    name: str
    outcome: InputOutcome
    detail: str | None = None

    def as_dict(self) -> dict:
        return {"input": self.name, "outcome": self.outcome.value, "detail": self.detail}


@dataclass
class EvidenceInputsManifest:
    """Ordered record of inputs for one request. Append-only by construction —
    an input's outcome is stated once, when it is known."""

    inputs: list[EvidenceInput] = field(default_factory=list)

    def record(self, name: str, outcome: InputOutcome, detail: str | None = None) -> None:
        self.inputs.append(EvidenceInput(name=name, outcome=outcome, detail=detail))

    def as_list(self) -> list[dict]:
        return [entry.as_dict() for entry in self.inputs]

    def outcome_of(self, name: str) -> InputOutcome | None:
        for entry in self.inputs:
            if entry.name == name:
                return entry.outcome
        return None

    def any_degraded_or_missing(self) -> bool:
        """Whether anything fell short of USED/NOT_APPLICABLE — the coarsest
        question the confidence tier will ask of this record."""
        return any(
            entry.outcome in (InputOutcome.DEGRADED, InputOutcome.UNAVAILABLE)
            for entry in self.inputs
        )
