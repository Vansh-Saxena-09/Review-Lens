"""Validate Amazon listing links and present user-supplied checks, not verdicts.

It cannot verify products or sellers; retrieved review text is analyzed separately.
"""
import re
from urllib.parse import urlsplit
from amazon_fetch import fetch_listing

AMAZON_DOMAINS = {
    "amazon.com", "amazon.in", "amazon.co.uk", "amazon.ca", "amazon.com.au",
    "amazon.de", "amazon.fr", "amazon.it", "amazon.es", "amazon.co.jp",
    "amazon.com.br", "amazon.com.mx", "amazon.ae", "amazon.sa", "amazon.sg",
    "amazon.nl", "amazon.se", "amazon.pl", "amazon.com.tr", "amazon.eg",
}
ASIN_PATH = re.compile(r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:/|$)", re.IGNORECASE)


def parse_amazon_url(url: str) -> dict:
    try:
        parsed = urlsplit(url.strip())
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid Amazon product URL.") from exc
    if (parsed.scheme.lower() != "https" or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or host not in AMAZON_DOMAINS | {"www." + d for d in AMAZON_DOMAINS}):
        raise ValueError("Use a direct HTTPS product link on a supported Amazon marketplace.")
    match = ASIN_PATH.search(parsed.path)
    if not match:
        raise ValueError("Use a direct Amazon product URL containing /dp/ or /gp/product/ and a 10-character product ID. Short links are not supported.")
    asin = match.group(1).upper()
    domain = host.removeprefix("www.")
    return {"asin": asin, "marketplace": domain, "canonical_url": f"https://www.{domain}/dp/{asin}"}


def assess_listing(payload, model, fetcher=fetch_listing) -> dict:
    listing = parse_amazon_url(payload.url)
    retrieval = fetcher(listing['marketplace'], listing['asin'])
    reviews = retrieval.pop('reviews', [])
    analyzed = []
    if model.loaded:
        for text in reviews:
            label, probability, confidence = model.predict(text)
            analyzed.append({'text': text, 'label': label, 'confidence': round(confidence, 6), 'probability_cg': round(probability, 6)})
    retrieval['reviews_found'] = len(reviews)
    retrieval['reviews_analyzed'] = len(analyzed)
    retrieval['review_results'] = analyzed
    retrieval['model_available'] = model.loaded
    retrieval['model_version'] = getattr(model, 'version', None)
    checks = []
    checks.append({"title": "Listing link", "detail": "The address has a supported Amazon domain and product ID. This does not confirm the item exists or is genuine.", "state": "provided"})
    for title, value in (("Seller", payload.seller), ("Brand", payload.brand), ("Listing title", payload.title), ("Price", payload.price)):
        if value and value.strip():
            checks.append({"title": title, "detail": value.strip(), "state": "user_supplied"})
    if payload.seller_authorized == "yes":
        checks.append({"title": "Seller authorization", "detail": "You indicated that the seller is authorized. This has not been independently verified.", "state": "user_supplied"})
    elif payload.seller_authorized == "no":
        checks.append({"title": "Seller authorization", "detail": "You indicated that the seller is not authorized. Check directly with the brand; this does not establish that the item is counterfeit.", "state": "attention"})
    review_signal = None
    if payload.review_text and payload.review_text.strip():
        if model.loaded:
            label, probability, confidence = model.predict(payload.review_text.strip())
            review_signal = {"label": label, "confidence": round(confidence, 6), "probability_cg": round(probability, 6),
                "explanation": "Estimate of review-writing patterns only. It does not assess product authenticity, seller reliability, or whether a review is truthful."}
        else:
            checks.append({"title": "Review text", "detail": "Review-writing analysis is unavailable because the model is not loaded.", "state": "unavailable"})
    return {**listing, "status": "inconclusive", "checks": checks, "review_signal": review_signal, "retrieval": retrieval,
        "next_steps": ["Check whether the seller is listed as authorized by the manufacturer.", "Compare the product details and price with the manufacturer's official listing.", "Check return terms, packaging and serial or lot identifiers with the manufacturer when available."],
        "limitations": ["User-entered details are not independently verified. Retrieved reviews, if available, are only a small sample and may not be representative.", "A product link, listing text, or review-writing estimate cannot establish authenticity.", "Only the manufacturer or an appropriate physical inspection may be able to verify the item."],
        "warning": "Authenticity cannot be determined from this information. This is not a fake-or-genuine verdict."}
