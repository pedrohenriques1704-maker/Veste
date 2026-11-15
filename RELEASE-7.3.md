# VESTE 7.3 — release checklist (P2)
Status: implementation staged on feature/p2-smart-shopping; do not merge before preparing the production configuration. Main and Netlify production have not been modified by this release.
 
## Scope
- Existing Discover / Radar UI, no added end-user navigation and no Awin configuration exposed to common users.
- Index 0–100, personalized P1 signals, duplicate warning and alternatives, bounded outfit collages and cost per potential combination. It is a heuristic, not a probability.
- Saved offers: availability, source date, price history, target/drop alerts when catalog is refreshed in-app. Not push notifications.
- Separate /admin/ page with signed-in session, server-checked administrator allowlist, aggregate visits and Awin-attributed sales/commissions. Awin management and workflow links are restricted by the admin screen and by the destination platforms' own authentication.
- Independent daily GitHub Actions import at 08:15 UTC (05:15 BRT), plus manual trigger.
 
## Before deployment — credentials
In repository Settings > Secrets and variables > Actions, configure **repository secrets**, never commit or paste tokens in chat:
- AWIN_FEED_KEY — product feed API key (not the same as publisher token)
- AWIN_API_TOKEN — publisher API token for transaction reports
- SUPABASE_SERVICE_ROLE_KEY — legacy service-role JWT, stored only in Actions secrets.
In the Variables tab set AWIN_PUBLISHER_ID and optionally AWIN_MERCHANT_IDS (default: 118977, Lauri Esporte). Only explicitly approved merchants with a single supported standard Awin CSV feed. Enhanced Google JSONL is not enabled by this release; it needs a separately verified adapter and tracking-link strategy. Do not enable unknown advertisers or override catalog safeguards to make a failing run succeed.
 
## Deploy order
1. Run local/CI validation (`node --check app.js`, `node tests/p2-shopping.cjs`, `python3 -m unittest discover -s tests -p 'test_*.py'`). Confirm branch checks; no production data used by these tests.
2. Apply `supabase/p2-commerce.sql` as a production migration via privileged database access. It is additive and does not delete closet data. Provision ONLY the explicitly confirmed owner's auth user ID with an insert into `veste_private.commerce_admins(user_id)` (never guess based on account creation order).
3. Merge the reviewed branch into main once release is authorized. Netlify auto deployment should run once; verify its commit and the service worker cache veste-pwa-v7-3-0. No deploy was triggered while staging. Confirm the commercial disclosure requirements under local rules and partner terms before publishing affiliate offers; no permanent commission copy was inserted on request.
4. In GitHub Actions, run VESTE commerce sync manually. Confirm Awin source permissions, expected stock/range, existing Lauri IDs, number of imported products, no unexpected product retirement, redacted logs, report timestamp. A failure must preserve the existing catalog rather than disable it. After success, schedule runs daily independently of Netlify. Do not claim end-to-end Awin success until this run passes with real credentials.
5. Sign into VESTE and verify Discover > Radar: scores, actual photos, alternatives, saved products and price alerts. Check empty closet, mobile layout and PWA upgrade. Visit /admin/ as the owner; test denial with a common account. Validate a tracked link without making purchases. Check closet data, existing navigation and account sync.
6. If a frontend defect occurs, roll back Netlify to the previous working deploy; keep the additive private tables and disable the workflow if integration fails. No secret values belong in GitHub source or logs.
 
## Verified during development
- 21 extracted JS checks with simulated browser dependencies (URL shim), including score range, redundancy, missing data, stock, alerts; app source parses; index.html and experienceV7() exactly match main.
- 6 Python unit tests on source/test files locally copied with matching Git blob hashes; live Awin credentials not used.
- 15 SQL checks succeeded in rollback transactions on the connected database, including full snapshot of real 743-row Lauri catalog, partial-feed rejection, grants, unauthorized users, click validity, partner totals and attribution. After tests catalog still held 743 available products; commerce RPCs not installed until release.
- Browser UI and end-to-end authenticated live network tests remain deployment smoke checks. GitHub Actions run status not verified from connector.
 
## References
- https://help.awin.com/developers/docs/downloading-a-list-of-your-product-feeds
- https://help.awin.com/developers/docs/hosting-feeds
- https://help.awin.com/apidocs/returns-a-list-of-transactions-for-a-given-publisher
- https://help.awin.com/developers/docs/click-appends-dyn-params
- https://help.awin.com/apidocs/retail-publisher-productapidocumentation-1
