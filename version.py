"""Single source of truth for the WolfeyBot / decision-engine version.

Bump ``__version__`` here (and add a matching ``CHANGELOG.md`` entry) on every
release.  Everything else derives from this one line:

* ``main.py`` imports it as ``VERSION`` — drives the ``Battle Data/<version>/``
  log folder and the ``version`` field in ``elo_log.json``.
* ``_gen_turn1_summary.py`` stamps it into the ``turn1_summary.md`` header.
* ``tests/test_turn1_decisions.py`` asserts the regenerated summary header
  matches, so a bump that forgets to regenerate the summary fails CI.

The only spots that still hold the number by hand are the human-facing docs
(``CHANGELOG.md`` release notes); ``CLAUDE.md`` points here rather than copying it.
"""

__version__ = "0.8.10"
