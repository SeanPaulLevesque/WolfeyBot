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

`teams.json` binds a team to an **account name** (a key in `bot_secrets.PROFILES`),
never to raw credentials — creds stay in the git-ignored `bot_secrets.py`.

## Running

```
python main.py --team meta-team           # current version, on meta-team's account
python main.py --team meta-team@v1         # pin a specific version to A/B vs @v2
python main.py --team off-meta-team        # logs into the alt account automatically
python main.py --list-teams                # list teams, versions, accounts (validates each)
```

No `--team` falls back to the repo-root `team.txt`, which is the **frozen baseline**
that `turn1_summary.md` and the test suite are built from. Iterating a team under
`teams/` does **not** move that baseline.

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
3. Add the account to `bot_secrets.PROFILES` if it's new (username + password).
