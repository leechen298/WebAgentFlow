"""Static analysis helpers that operate on HTML strings.

This sub-package is for pure-function utilities that take DOM/HTML
as input and return structured analysis — no Playwright, no DB, no
runtime state. Keeping them out of ``services/learning/`` (which is
the autonomous-exploration runtime pipeline) so they can be reused
from recording, replay, and future offline tooling without
cross-package import awkwardness.
"""
