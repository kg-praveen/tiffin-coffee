---
name: simulate
description: UC5 — "run the simulation", "stress test the engine", "what if Nifty falls 15%", "what would the plate be if INFY drops 10%", "what if G-sec goes up 50bp". Replays a recorded (or live) market day through the real morning board and plate under shocks and checks every law on every plate. Rehearsal only — never an order.
---
# Market simulation (UC5)

1. **Which mode?**
   - Stress test / "is the engine safe?" → `uv run python -m usecases.simulate run`
     (all scenarios; add `--amount 10000 --amount 40000` for several session sizes,
     `--scenario hockey_rung1` to pick one).
   - What-if → `uv run python -m usecases.simulate what-if --nifty -15 --name INFY:-10
     --sector LENDER:-12 --gsec-bp 50 --days 30 --amount 25000` (any subset).
   - Default market = newest recording in `tests/fixtures/market/`. Say its date.
     `--live` fetches today's market instead (network). `record` saves a new recording —
     only when Praveen asks; it becomes the CI baseline once committed.
2. **Answer verdict first.** `run`: PASS/FAIL and how many runs. Any VIOLATION = the
   engine broke a law → say "do not trust today's plate — NO ACTION" and name it.
   `what-if`: the plate difference name by name, then which triggers would fire.
3. Then FINDINGS (legal per spec, Praveen's call — e.g. the 1-share floor spending past a
   small session, breadth outside 8-15) and the NOT MODELLED note (HOCKEY on
   Nifty −5% wk / name −10% day has no engine input yet).
4. One `UC5_SIMULATION` session row is written (skip with `--no-session`). Simulated
   plates are never written as UC2 sessions — a rehearsal is not a decision.
5. Never present a what-if plate as something to buy. If Praveen wants to act, run the
   real `plate` skill on live prices.
