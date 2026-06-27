"""lead_stats.py — Opponent lead frequency statistics.

Tracks which Pokémon opponents lead with against our team, accumulated
across all recorded battles from v0.5.0 onward.  Used by team_preview
to predict likely opponent leads and optimise our own lead order.

Data persisted at:
    Battle Data/lead_stats.json

Schema::

    {
        "total_battles": 42,
        "counts": {
            "Farigiraf": 10,
            "Charizard": 7,
            ...
        },
        "pairs": {
            "Garchomp|Whimsicott": 8,
            "Charizard|Whimsicott": 3,
            ...
        }
    }

``counts`` are per-individual-slot, not per-battle: a battle where Farigiraf
and Charizard both led increments each species by 1 (total_battles by 1).

``pairs`` are per-battle co-occurrence: that same battle increments the single
sorted key ``"Charizard|Farigiraf"`` by 1.  This captures which two mons are
actually led *together* — two independently-popular leads (e.g. Whimsicott and
Farigiraf, each a top individual lead but co-led only ~1% of the time) must not
be predicted as a pair just because each leads often on its own.
"""
from __future__ import annotations

import itertools
import json
import os
import pathlib

_PROJECT_ROOT = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
_STATS_FILE   = _PROJECT_ROOT / "Battle Data" / "lead_stats.json"

_PAIR_SEP = "|"   # joins a sorted (a, b) into one dict key: "A|B"

# Co-led count a candidate pair must reach before we predict it outright (below
# this we fall back to anchoring on the strongest single + its real partner).
PAIR_MIN_SUPPORT = 2


def pair_key(a: str, b: str) -> str:
    """Canonical (order-independent) key for a lead pair: ``"A|B"`` sorted."""
    return _PAIR_SEP.join(sorted((a, b)))


def _load() -> dict:
    """Read the stats file; return a blank structure if absent or unreadable."""
    if _STATS_FILE.exists():
        try:
            with open(_STATS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("pairs", {})   # tolerate older pair-less files
                return data
        except Exception:
            pass
    return {"total_battles": 0, "counts": {}, "pairs": {}}


def _save(data: dict) -> None:
    _STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public read API ───────────────────────────────────────────────────────────

def lead_frequency(species: str) -> int:
    """Number of times *species* has been seen as an opponent lead."""
    return _load()["counts"].get(species, 0)


def all_lead_counts() -> dict[str, int]:
    """Return ``{species: count}`` for all seen leads, sorted by count descending."""
    data = _load()
    return dict(sorted(data["counts"].items(), key=lambda x: -x[1]))


def lead_pair_frequency(a: str, b: str) -> int:
    """Number of battles *a* and *b* were led **together** (order-independent)."""
    if not a or not b or a == b:
        return 0
    return _load().get("pairs", {}).get(pair_key(a, b), 0)


def pair_partner_counts(species: str) -> dict[str, int]:
    """``{partner: co-led count}`` for every species *species* has been led with,
    sorted by count descending."""
    out: dict[str, int] = {}
    for key, count in _load().get("pairs", {}).items():
        a, b = key.split(_PAIR_SEP, 1)
        if a == species:
            out[b] = count
        elif b == species:
            out[a] = count
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def all_lead_pairs() -> dict[str, int]:
    """Return ``{"A|B": count}`` for all co-led pairs, sorted by count descending."""
    data = _load()
    return dict(sorted(data.get("pairs", {}).items(), key=lambda x: -x[1]))


def total_battles() -> int:
    """Total number of battles recorded in the lead stats."""
    return _load().get("total_battles", 0)


# ── Public write API ──────────────────────────────────────────────────────────

def reset() -> None:
    """Clear all accumulated lead stats (writes a blank structure).

    Used to drop a stale prior — e.g. the Reg M-A-derived counts when the
    ladder rolls to M-B — before reseeding from recent battles
    (``tools/seed_lead_stats.py``).
    """
    _save({"total_battles": 0, "counts": {}, "pairs": {}})


def record_leads(leads: list[str]) -> None:
    """Increment lead counts for each species in *leads* and persist.

    Bumps each species' individual ``counts``, every co-led ``pairs`` key (one
    for a normal 2-mon doubles lead), and ``total_battles`` by 1 regardless of
    how many leads are provided.

    Non-empty species strings only; blank entries are silently skipped.
    """
    data   = _load()
    counts = data.get("counts", {})
    pairs  = data.get("pairs", {})
    present = [s for s in leads if s]
    data["total_battles"] = data.get("total_battles", 0) + 1
    for s in present:
        counts[s] = counts.get(s, 0) + 1
    for a, b in itertools.combinations(sorted(set(present)), 2):
        key = pair_key(a, b)
        pairs[key] = pairs.get(key, 0) + 1
    data["counts"] = counts
    data["pairs"]  = pairs
    _save(data)


# ── Prediction ────────────────────────────────────────────────────────────────

def predict_pair(species_list: list[str],
                 *, pair_min: int = PAIR_MIN_SUPPORT) -> list[str]:
    """Predict the two species an opponent will lead, from their previewed team.

    Three tiers, most-to-least evidence:

    1. **Confident co-lead** — the candidate pair (out of all C(n,2) from
       *species_list*) seen led together the most, if that reaches *pair_min*.
       This is what stops two independently-popular-but-rarely-together leads
       (Whimsicott + Farigiraf) from being predicted as a pair.
    2. **Anchor + real partner** — otherwise anchor on the single most-frequent
       lead and pair it with whichever previewed mon it's *actually* co-led with
       most (any positive co-lead count).  Avoids re-pairing two supports.
    3. **Top-2 singles** — only when we have no co-lead evidence for this team at
       all, fall back to the two highest individual lead frequencies (the old
       behaviour).

    Returns up to two species (fewer only if *species_list* has fewer)."""
    species = [s for s in species_list if s]
    if len(species) < 2:
        return list(species)

    # 1. Confident co-led pair.
    best_pair: list[str] | None = None
    best_freq = -1
    for a, b in itertools.combinations(species, 2):
        f = lead_pair_frequency(a, b)
        if f > best_freq:
            best_freq, best_pair = f, [a, b]
    if best_pair is not None and best_freq >= pair_min:
        return best_pair

    # 2. Anchor on the strongest individual lead + its most-co-led partner.
    anchor = max(species, key=lead_frequency)
    partners = [s for s in species if s != anchor]
    partner = max(partners, key=lambda s: lead_pair_frequency(anchor, s))
    if lead_pair_frequency(anchor, partner) > 0:
        return [anchor, partner]

    # 3. No co-lead evidence: the original top-2 individual frequencies.
    return sorted(species, key=lead_frequency, reverse=True)[:2]
