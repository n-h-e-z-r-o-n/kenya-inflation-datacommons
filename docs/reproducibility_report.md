# Pipeline reproducibility and idempotence check

Source snapshot: `data\source\cbk_inflation_2026-10-14.html`

The same archived source was processed and imported twice against the **same SQLite database** without deleting it between runs. The generated observations and loaded rows were compared.

- First run: 282 database rows; 0 duplicate keys; readback PASS
- Second run: 282 database rows; 0 duplicate keys; readback PASS
- Loaded data checksum identical: `057a0a89acd329761e52a2009954b94067386668aeb92b1cb948f9ab6c661852`
- Generated CSV checksum identical: `a1fccc89cc493b33d2f3a42fa2c8f9e5823c9320522362d0f3723321ef1fdfd6`
- Result: **PASS — no duplicates added on the second run.**
