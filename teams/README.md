# Named teams & A/B testing

Two independent axes, plus the engine version:

| Axis | Where it lives | A/B workflow | Account |
|---|---|---|---|
| **Engine version** | `version.py` (`__version__`) | hold team fixed, vary engine | — |
| **Team name** | `teams/<name>/` | distinct rosters, compared across accounts | **one account per named team** |
| **Team version** | `teams/<name>/v<n>.txt` | roster iterations A/B'd against each other | **same account** |

So *team-version changes* run on the **same account** (clean A/B of a tweak), and
*different named teams* run on **different accounts**.

## Layout

```
teams/
  teams.json          # name -> {label, account, current version}
  meta-team/
    v1.txt            # Showdown paste, one file per version
    v2.txt            # (add when you iterate)
  off-meta-team/
    v1.txt
```

`teams.json` binds a team to an **account** — the Showdown username, which is
also the key in `bot_secrets.PROFILES`. It never holds raw credentials; only the
password lives in the git-ignored `bot_secrets.py`. Keying profiles by username
keeps `teams.json` self-documenting and scales to any number of accounts.

## Running

```
python main.py --team meta-team           # current version, on meta-team's account
python main.py --team meta-team@v1         # pin a specific version to A/B vs @v2
python main.py --team off-meta-team        # logs into off-meta's account (DongQuixote3)
python main.py --list-teams                # list teams, versions, accounts (validates each)
```

No `--team` falls back to `snapshots/baseline_team.txt`, the **frozen baseline**
roster that the decision snapshots (`snapshots/<scenario>/baseline.md`) and the
test suite are built from. Iterating a team under `teams/` does **not** move that
baseline — it lives in the snapshots subsystem, separate from these ladder teams.

## Data separation

Every battle and ELO record is filed under, and tagged with, its team + version:

```
Battle Data/<engine_version>/<team_name>/<team_version>/<battle_id>.json
   e.g.  Battle Data/0.9.0/meta-team/v1/   vs   Battle Data/0.9.0/meta-team/v2/
```

An A/B comparison is then just diffing two folders (or filtering logs by the
`team` / `team_version` / `username` tags).

## Adding a team / version

1. Drop a Showdown paste at `teams/<name>/v<n>.txt`.
2. Add/point the entry in `teams.json` (`account`, `current`).
3. If the account is new, add `"<username>": {"password": "..."}` to
   `bot_secrets.PROFILES` and reference `"<username>"` as the team's `account`.
