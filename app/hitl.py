"""Human-in-the-loop helpers shared by the CLI and the graph."""

APPROVAL_ANSWERS = frozenset({"yes", "y", "true", "approve", "approved"})


def parse_approval(answer: object) -> bool:
    """Return ``True`` only for an explicit affirmative answer.

    Empty input, ``"no"``, ``"n"``, ``"false"`` and any unrecognised value are
    treated as rejection. This keeps a stray keypress from approving code.
    """
    return str(answer).strip().lower() in APPROVAL_ANSWERS
