import io
import sys
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from amazon_fetch import fetch_listing, MAX_BYTES
from link_assessment import assess_listing
from schemas import AmazonAssessmentInput

class Response:
    def __init__(self, data, url='https://www.amazon.in/dp/B012345678', content_type='text/html'):
        self.data, self.url = data, url
        self.headers = Message()
        self.headers['Content-Type'] = content_type
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def geturl(self): return self.url
    def read(self, limit): return self.data[:limit]

class Opener:
    def __init__(self, response): self.response = response; self.url = None
    def open(self, request, timeout):
        self.url = request.full_url
        if isinstance(self.response, Exception): raise self.response
        return self.response

class Model:
    loaded = True
    version = 'test'
    def predict(self, text): return ('CG', 0.8, 0.8)

class RetrievalTests(unittest.TestCase):
    def test_real_extracted_review_is_classified(self):
        page = b'<html><span id="productTitle">Example item</span><div data-hook="review-body"><span>Actual review text.</span></div></html>'
        opener = Opener(Response(page))
        def fetch(market, asin): return fetch_listing(market, asin, opener)
        result = assess_listing(AmazonAssessmentInput(url='https://amazon.in/dp/B012345678?tag=secret'), Model(), fetch)
        self.assertEqual(opener.url, 'https://www.amazon.in/dp/B012345678')
        self.assertEqual(result['retrieval']['title'], 'Example item')
        self.assertEqual(result['retrieval']['review_results'][0]['text'], 'Actual review text.')
        self.assertEqual(result['retrieval']['reviews_analyzed'], 1)
        self.assertEqual(result['status'], 'inconclusive')

    def test_jsonld_and_no_review(self):
        page = b'<script type="application/ld+json">{"@type":"Product","name":"Item"}</script>'
        result = fetch_listing('amazon.in', 'B012345678', Opener(Response(page)))
        self.assertEqual(result['title'], 'Item')
        self.assertEqual(result['reviews'], [])

    def test_blocked_redirect_oversize_and_timeout(self):
        cases = [Response(b'captcha robot check'), Response(b'hello', url='https://evil.test/'), Response(b'x' * (MAX_BYTES+1)), URLError('timeout'), Response(b'{}', content_type='application/json')]
        for case in cases:
            with self.subTest(case=type(case).__name__):
                self.assertEqual(fetch_listing('amazon.in', 'B012345678', Opener(case))['status'], 'unavailable')

    def test_model_unavailable_does_not_invent_prediction(self):
        class Missing: loaded = False
        result = assess_listing(AmazonAssessmentInput(url='https://amazon.in/dp/B012345678'), Missing(), lambda *_: {'status':'retrieved','reviews':['Real text']})
        self.assertEqual(result['retrieval']['reviews_found'], 1)
        self.assertEqual(result['retrieval']['reviews_analyzed'], 0)
        self.assertEqual(result['retrieval']['review_results'], [])

if __name__ == '__main__': unittest.main()
