"""tools/seed_supplement_from_pikalytics.py — convert scraped Pikalytics Reg M-B
usage into data/sets_supplement.json entries.

Reads data/pikalytics_regmb_raw.json (populated by WebFetch, one object per base
species):

    {"Staraptor": {"items": {...}, "abilities": {...}, "moves": {...},
                   "spreads": [{"nature": "...", "ev": "h/a/d/sa/sd/sp", "pct": n}, ...]}, ...}

Normalisation to match the Smogon-style convention the engine expects:
  * Mega-stone handling: Pikalytics files the stone as the BASE form's top item.
    For a mega-capable mon we split into a "<X>-Mega" entry (stone as its only
    item -> wires mega_stones / mega_forme_for_stone) and a base "<X>" entry with
    the stone removed and the remaining items renormalised (so its top item is
    the next real item). raw_count is set from the stone's usage so assumed_forme
    picks the right side. The mega entry's ability comes from our species data
    (the forme-fixed mega ability), not Pikalytics' pre-mega ability.
  * Spreads are kept top-N (Smogon-like granularity); EV strings are already in
    our 0-32 SP format.
  * Teammates: Pikalytics only exposes order, so any log-derived teammate %s
    already in the supplement are preserved.

Supersedes the log-seeded entries.  Run AFTER scraping:
    .venv\\Scripts\\python.exe tools/seed_supplement_from_pikalytics.py
"""
import sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from data import get_species, ability_of

RAW  = os.path.join(ROOT, "data", "pikalytics_regmb_raw.json")
SUPP = os.path.join(ROOT, "data", "sets_supplement.json")
TOP_SPREADS = 8
TOP_MOVES   = 14


def _is_stone(item: str) -> bool:
    return item.endswith("ite") and item != "Eviolite"


def _mega_formes(base: str) -> list:
    return [f for f in (f"{base}-Mega", f"{base}-Mega-X", f"{base}-Mega-Y")
            if get_species(f) is not None]


def _renorm(d: dict) -> dict:
    tot = sum(d.values())
    if tot <= 0:
        return {}
    return {k: round(v * 100.0 / tot, 1) for k, v in d.items()}


def _top_moves(moves: dict) -> dict:
    return dict(sorted(moves.items(), key=lambda kv: -kv[1])[:TOP_MOVES])


def _spreads(rows: list) -> dict:
    out = {}
    for r in sorted(rows, key=lambda r: -r.get("pct", 0)):
        ev = (r.get("ev") or "").strip()
        # Skip nature-only aggregate rows: blank, or all-zero EVs (some pages
        # encode the per-nature total as "0/0/0/0/0/0").
        if not ev or all(c.strip() in ("", "0") for c in ev.split("/")):
            continue
        out[f"{r['nature']}:{ev}"] = r["pct"]
        if len(out) >= TOP_SPREADS:
            break
    return out


def _stone_for_mega(base: str, mega: str, items: dict):
    """The stone item powering *mega*: the matching '…ite' item from the page."""
    stones = [it for it in items if _is_stone(it)]
    if not stones:
        return None
    if len(stones) == 1:
        return stones[0]
    # Multi-mega (Raichu-Mega-X/-Y): match the stone whose suffix matches.
    suffix = mega.rsplit("-", 1)[-1] if mega.endswith(("-X", "-Y")) else ""
    for s in stones:
        if suffix and s.endswith(suffix):
            return s
    return stones[0]


def main() -> None:
    raw = json.load(open(RAW, encoding="utf-8"))
    doc = json.load(open(SUPP, encoding="utf-8"))

    # Preserve log-derived teammate %s.  Overlay rather than wipe: Pikalytics
    # supersedes per-mon where present, but entries for mons not yet scraped
    # (still log-seeded) are retained so a partial run loses nothing.
    old_teammates = {k: v["teammates"] for k, v in doc.items()
                     if not k.startswith("_") and isinstance(v, dict) and v.get("teammates")}
    prev_seeded = doc.get("_seeded", [])

    entries = {}
    for X, d in raw.items():
        items = {k: v for k, v in (d.get("items") or {}).items() if v > 0}
        abilities = {k: v for k, v in (d.get("abilities") or {}).items() if v > 0}
        moves = _top_moves({k: v for k, v in (d.get("moves") or {}).items() if v > 0})
        spreads = _spreads(d.get("spreads") or [])
        megas = _mega_formes(X)
        stone = next((it for it in items if _is_stone(it)), None)

        # Gap-fill precedence is enforced by the supplement loader (main file
        # always wins), so we write entries unconditionally here.
        if megas and stone:
            stone_pct = max(items.get(s, 0) for s in items if _is_stone(s))
            base_items = _renorm({it: v for it, v in items.items() if not _is_stone(it)})
            entries[X] = {"raw_count": round((100 - stone_pct) * 10),
                          "abilities": abilities, "items": base_items,
                          "moves": dict(moves), "spreads": dict(spreads)}
            for M in megas:
                mstone = _stone_for_mega(X, M, items)
                mab = ability_of(M)
                entries[M] = {"raw_count": round(stone_pct * 10),
                              "abilities": ({mab: 100.0} if mab else dict(abilities)),
                              "items": {mstone: 100.0} if mstone else {},
                              "moves": dict(moves), "spreads": dict(spreads)}
        else:
            entries[X] = {"abilities": abilities, "items": items,
                          "moves": dict(moves), "spreads": dict(spreads)}

    # Carry over preserved teammates, then write.
    for name, e in entries.items():
        if name in old_teammates:
            e["teammates"] = old_teammates[name]
    doc["_provenance"] = ("_seeded entries are tool-seeded prelim usage: Pikalytics "
                          "Reg M-B where scraped (data/pikalytics_regmb_raw.json, via "
                          "tools/seed_supplement_from_pikalytics.py) — mega stones "
                          "normalised onto the -Mega entry, teammates kept from logs — "
                          "else battle-log fallback for mons not yet scraped.")
    for name, e in sorted(entries.items(), key=lambda kv: -kv[1].get("raw_count", 0)):
        doc[name] = e
    doc["_seeded"] = sorted(set(prev_seeded) | set(entries))
    json.dump(doc, open(SUPP, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(SUPP, "a", encoding="utf-8").write("\n")

    print(f"seeded {len(entries)} entries from {len(raw)} Pikalytics pages")
    for name in sorted(entries):
        e = entries[name]
        it = next(iter(e["items"]), "-")
        print(f"  {name:22s} top_item={it:16s} moves={len(e['moves'])} spreads={len(e['spreads'])}")


if __name__ == "__main__":
    main()
