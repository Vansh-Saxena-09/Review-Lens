# Handoff

The local FastAPI/static frontend includes a real review-writing classifier and a best-effort Amazon India public-listing retrieval flow. The classifier estimates CG versus OR writing patterns and cannot determine product authenticity or review truth. Listing checks are not persisted; standalone review submissions are stored locally in SQLite.

Thirteen backend tests passed. Mocked retrieval verified extraction and classification of actual fixture review text. A live request for `B0CWTQMSSQ` returned the correct product title after a parser correction, but no review text. No live review prediction from that listing was possible. The corrected result was checked directly with the retrieval function; browser verification after that correction remains outstanding. Other marketplaces, CSV export, mobile layout, and restart persistence are not fully verified.

Amazon can block automated access or omit reviews. No CAPTCHA, authentication or redirect bypass is implemented. See `PROJECT_STATUS.md`. Do not silently delete SQLite history or replace model artifacts.
