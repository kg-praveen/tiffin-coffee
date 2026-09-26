-- Migration 006: FMCG brand ownership (osep v7 §G hard gate)
-- Date: 2026-09-26
--
-- Why: osep v7 §G FMCG/CONSUMER-BRAND — "HARD GATE: the company must OWN its brand"
-- (VBL/Pepsi worked case: "contract termination = business death"). Acceptance case 16.
-- brand_owned: 1 = owns its brands · 0 = does not · NULL = not recorded (the plate
-- fails closed and raises the name for Praveen — E4: never classified from memory).
-- Only VBL is STATED in the spec/register; every other FMCG name waits for Praveen.

ALTER TABLE names ADD COLUMN brand_owned INTEGER CHECK (brand_owned IN (0, 1));

UPDATE names SET brand_owned = 0 WHERE symbol = 'VBL';
