# WolfeyBot ELO trends

_Generated from `elo_log.json` — 2468 battles, 0.3.3 → 0.7.6._

![ELO over time](docs/elo_chart.svg)

> `elo_before` is the ladder rating at the **start** of each battle. ELO is noisy per-game (±~25); the per-version **mean** and the trend line are the reliable signals.

## Per-version summary

| Version | Battles | Win % | Mean ELO | Start→End ELO | Δ mean vs prev |
|---|---|---|---|---|---|
| 0.3.3 | 12 | 50% | 1202 | 1227→1200 |  |
| 0.3.4 | 18 | 61% | 1211 | 1224→1269 | +9 |
| 0.3.5 | 6 | 67% | 1287 | 1290→1323 | +76 |
| 0.4.0 | 40 | 40% | 1227 | 1337→1194 | -60 |
| 0.5.0 | 26 | 50% | 1156 | 1169→1176 | -71 |
| 0.5.1 | 9 | 78% | 1219 | 1151→1258 | +64 |
| 0.5.3 | 8 | 75% | 1314 | 1279→1346 | +95 |
| 0.5.4 | 35 | 40% | 1321 | 1370→1243 | +6 |
| 0.5.6 | 290 | 50% | 1228 | 1218→1173 | -92 |
| 0.6.5 | 2 | 0% | 1186 | 1196→1175 | -43 |
| 0.6.6 | 44 | 48% | 1162 | 1157→1153 | -23 |
| 0.6.7 | 189 | 48% | 1147 | 1000→1183 | -15 |
| 0.6.8 | 1606 | 50% | 1214 | 1165→1462 | +66 |
| 0.7.1 | 66 | 44% | 1404 | 1451→1280 | +190 |
| 0.7.5 | 12 | 58% | 1302 | 1253→1338 | -102 |
| 0.7.6 | 105 | 48% | 1294 | 1321→1133 | -9 |

**Peak elo_before:** 1555 (battle #2293, 0.7.1). **Overall:** 1227 → 1133 (-94 over the logged history).

**Overall trend:** +1.3 ELO per 100 battles (least-squares fit across all 2468). The latest version (0.6.8) climbed 1321→1133 over its 105 games and set the all-time peak — the clearest improvement signal, since cross-version *mean* ELO is confounded by where each version started on the ladder.