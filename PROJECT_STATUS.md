# Project status

## 13 November 2026

The replacement website uses a trained TF-IDF/calibrated linear SVM to estimate computer-generated versus original review-writing patterns. Its held-out random review-level test accuracy was 94.71% on 8,087 reviews; this is not a product-authenticity accuracy. Related or duplicate reviews may cross the split.

The Amazon India link checker now attempts to fetch the public listing and analyzes review text only if actually present in the response. It does not bypass CAPTCHA, authentication, or redirects and does not establish whether products are counterfeit. Other Amazon marketplaces are not automatically fetched. Listing checks are transient.

Thirteen backend tests passed, including mocked retrieval, blocked responses, limits, unavailable model, and classification of extracted fixture text. A live request to `amazon.in/dp/B0CWTQMSSQ` retrieved the product title but contained no review text, so no live review predictions were produced. The browser showed the no-review condition before a subsequent title-parser correction; the corrected title was verified directly via the retrieval function, not through a fresh browser run. Full CSV export, mobile and restart-persistence checks remain outstanding.

The app is local and unauthenticated; review text submitted to the standalone analyzer is stored in SQLite. Dataset provenance and redistribution rights should be confirmed independently. Automatic access is subject to Amazon availability and applicable terms.
