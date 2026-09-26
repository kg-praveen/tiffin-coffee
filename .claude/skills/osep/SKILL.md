---
name: osep
description: UC4 — "run OSEP on <stock>", "is <stock> a buy?", "underwrite <stock>", "re-derive the triggers" (after results). Runs the OSEP verdict per spec/osep-stock-analysis.SKILL.md v7 — data checks in code, judgments researched online with sources, verdict + trigger + expiry. Nothing enters the register until Praveen says yes.
---
# OSEP analyser (UC4)

1. **Run it:** `uv run python -m usecases.osep analyse SYMBOL` (new name: add
   `--ticker XYZ.NS --name "Company"`). It fetches price, company-reported EPS, book,
   promoter holding, debt, profit history and the live bond rate, and writes a session.
2. **If the verdict is INCOMPLETE, research the missing items yourself — never ask
   Praveen for a fact.** Use company filings, exchange announcements, Economic Times,
   Moneycontrol, Screener. For each answer record it with its source:
   `uv run python -m usecases.osep judge SYMBOL <item> <value> --source "<url or doc>"`
   Items: sovereign_directed · thesis_verifiable · governance_clean · industry_durable ·
   investable · stage1_score (0-50, Fisher-6) · thesis_type (RE-RATING / CYCLICAL /
   COMPOUNDER / INCOME / TURNAROUND) · promoter_exempt (banks, widely-held blue chips) ·
   sector_class (new names only — classify from what the company does, §SC, cite it).
   Then run step 1 again.
3. **Tell Praveen in plain words:** verdict first (good buy now / later / hard pass),
   trigger price and expiry, then 3-5 bullets on why, then what would change it.
   Point out if the new verdict differs from the register (e.g. "was GBN").
4. **Only on his yes:** `uv run python -m usecases.osep apply SYMBOL --reason "..."`
   — logs old → new with the reason (never overwritten) and updates bucket, expiry,
   thesis and the BUY trigger. Status (ADD/HOLD) stays his decision.
5. **After quarterly results:** `uv run python -m usecases.osep rederive` lists every
   active trigger recomputed on fresh EPS / book — old vs new. Nothing is written;
   re-run step 1-4 on the names that moved.
