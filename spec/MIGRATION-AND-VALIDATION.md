# PATTAZ ENGINE — Migration & Validation (17-Sep-2026)

## What this bundle is
Five rebuilt skills implementing Praveen's redesign decree (15-Sep): **rules, doctrine,
state and market data separated; no prices/costs/triggers in any skill; sector
classification at runtime; single-definition rules; fail-closed everywhere.**
- `pattaz-book` **v8** — state & identity (numbers migrated out; §-numbering preserved)
- `osep-stock-analysis` **v7** — THE ENGINE: E-laws E1-E9 + runtime classification (SC)
  + provenance-tagged sector gate table (G) + all prior stages/patch history
- `tiffin-coffee` **v6** — defect-2 fixed (lender = justified P/B ONLY); E-laws bound
- `finance-memory` **v6** — doctrine layer aligned (Principle-7 retagged; identity closed)
- `trigger-check` **v2** — seed board KILLED; ledger-only triggers; validity gate
Plus `LEDGER-APPENDIX.md` (every migrated number, dated — fold into the master, then
discard) and `validate.sh` (static suite — **18/18 PASS**, output below).

## Install
Replace each skill via the usual upload path, then run the INSTALL CHECK (book §21):
a fresh chat must show v8/v7/v6/v6/v2. `/mnt/skills` is a stale snapshot — verify via
the live registry description, never the mount (§9).
Then: append LEDGER-APPENDIX to the master ledger (or fold in wholesale) and trash
the appendix. Owed ledger entries are listed in appendix §G.

## Honest limits (read once)
No rule set "can never go wrong." What this design guarantees instead: **every
historically-observed failure now either fails a grep (static) or dead-ends in NO
ACTION with a named missing input (behavioral).** New failure modes remain possible;
the register (§9) is how they become impossible twice. Residual risks: web quotes can
be wrong (mitigated: multiple-source on decisions, screenshot-beats-tooling);
classification of a genuinely novel business is judgment (mitigated: strictest-gate +
🔴 flag); and the engine cannot stop a deliberate override (by design — overrides are
logged CONVICTION-OVERRIDE, never relabelled).

## Static suite — final run
All 18 tests PASS (defect-1/2/3 dead · seed board dead · no market numbers or costs
in skills outside tags · single-definition · cross-refs · version pins · rejected
forms logged · E-laws present and cited · identity closed · FMCG gate · insurer
retag). Re-runnable any time: `bash validate.sh`.

## Behavioral regression — 22 cases, replayed against the new engine
Legend: expected = the decision Praveen already approved, or the safe outcome.
| # | Case (source of truth) | Engine path | Result |
|---|---|---|---|
| 1 | Muthoot add (unlocked 05-Sep) | SC→LENDER · G-LENDER justified P/B (fresh ROE) · P5 DISAGREE note exists · starter size | ✅ unchanged — the research doc's raw Rec-1 would have re-locked it; REJECTED form logged |
| 2 | HDFC first-bite at fresh low (10-Sep) | SC→LENDER · P/E cannot rescue P/B fail | ✅ now ZERO; 10-Sep plate logged as control exception (appendix §G1) |
| 3 | ICICI 1,300 GTT | trigger-check v2 loads ledger (CANCELLED); no seed board exists to resurrect it | ✅ cannot re-arm |
| 4 | Stale-basis trigger (the 5-week invalid-trigger incident) | v2 validity gate: basis predates last result → NOT ARMABLE, price never classified | ✅ fail-closed |
| 5 | Corporate-action stale trigger (HDFC 560-vs-419 case) | validity gate (c) trailing-12m corporate action → re-derive first | ✅ blocked |
| 6 | Unknown/new name | SC: unclassifiable → DEFAULT ladder + 🔴 Praveen flag | ✅ no silent guess |
| 7 | Conglomerate / ambiguous sector | SC edge rule → STRICTEST applicable gate | ✅ conservative by construction |
| 8 | Demerged TMCV | classify each entity fresh; E indeterminate → watch-only (osep v6 rule intact) | ✅ |
| 9 | ONGC cheapest-on-H | P1 sovereign → zero (overlay 2 intact) | ✅ |
| 10 | BoB 0.7x book | passes P/B, legacy-fraud flag + cell block hold | ✅ |
| 11 | IRFC buy-and-sell same session | sell-list overlay intact | ✅ blocked |
| 12 | Tata Sons "value-unlock" headline (14-Sep) | no-tip rule (§3) + G-HOLDCO: no cash mechanism = a tip; Tata Steel on §8 never-add | ✅ no action; watch the board resolution (§21) |
| 13 | Gold / GOLDBEES | G-NON-EARNING: no valuation gate; thermostat only | ✅ |
| 14 | NTPC GBN | REGULATED≠DIRECTED passes; default ladder on live data; conditional on Coal India exit | ✅ unchanged (killed RoE+yield line was never load-bearing) |
| 15 | Income sleeve (IndiGrid/Mindspace) | G-REIT: veto-INPUT only; sleeve = Praveen's framework; note owed (§10-0c); REJECTED blanket rule logged | ✅ sleeve decision preserved, unfunded, pending note |
| 16 | VBL | brand-ownership HARD gate fails adds; owned-status OPEN (§10-0b); cell state follows answer | ✅ surfaced, not silently resolved |
| 17 | Manappuram "better" 2025 quote used today | E2: doctrine ≠ live input; G-table footnote shows it fails today's gate | ✅ blocked as input |
| 18 | Dr Reddy's plate attempt | GUARDRAIL block (live probe) + Layer-3 open | ✅ |
| 19 | Missing 52-week low / unfetchable price | E3/E9: NO ACTION naming the missing input ("not found" ≠ a result) | ✅ |
| 20 | Caps-off invoked on a live consider | §12b UNRESOLVED → E6 HALT and ask; quality/safety gates never waived | ✅ |
| 21 | Wipro at its low | within-cell tie-break + swap-source status: first-bite max, no build | ✅ |
| 22 | Rule edit that leaves a stale duplicate (defect-1 replay) | E7 edit protocol + T1/T2/T6 greps catch it mechanically | ✅ now detectable |
**22/22 preserve approved decisions or fail closed. Zero collateral damage.
Calibration: gates only tightened — pass-rate cannot have loosened (osep metric).**

## Conflicts surfaced (not resolved — E6, Praveen's calls)
1. **US exposure:** §2 "zero" vs §15 "₹10k/mo running" — verify at broker; one answer
   also settles the §15 scaling question. 2. **VBL owned-or-not** (§10-0b).
3. **REIT note sign-off** (§10-0c). 4. **§12b caps-off vs cap** (standing).
5. **§14 gold fork** (standing).

## Deliberately NOT done
No Drive writes (ledger entries listed as owed, appendix §G — your book, your append).
No cyclical positive metric hard-coded (OPEN until Book Ch.6 is transcribed, §10-0e).
No change to any economic threshold — every [POLICY] constant is exactly as approved;
this release moved plumbing, not economics.
