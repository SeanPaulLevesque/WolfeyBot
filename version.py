"""Single source of truth for the WolfeyBot / decision-engine version.

Bump ``__version__`` here (and add a matching ``CHANGELOG.md`` entry) on every
release.  Everything else derives from this one line:

* ``main.py`` imports it as ``VERSION`` — drives the ``Battle Data/<version>/``
  log folder and the ``version`` field in ``elo_log.json``.
* ``tools/gen_snapshot.py`` stamps it into the
  ``snapshots/turn1_openings/baseline.md`` header.
* ``tests/test_turn1_decisions.py`` asserts the regenerated snapshot header
  matches, so a bump that forgets to regenerate it fails CI.

The only spots that still hold the number by hand are the human-facing docs
(``CHANGELOG.md`` release notes); ``CLAUDE.md`` points here rather than copying it.
"""

__version__ = "0.38.1"
