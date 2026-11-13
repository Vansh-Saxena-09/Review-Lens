import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from link_assessment import parse_amazon_url, assess_listing
from schemas import AmazonAssessmentInput

class UnavailableModel:
    loaded = False

class AmazonListingTests(unittest.TestCase):
    def test_normalizes_and_strips_tracking(self):
        result = parse_amazon_url('https://www.amazon.com/Some-title/dp/b012345678?tag=tracking#details')
        self.assertEqual(result['asin'], 'B012345678')
        self.assertEqual(result['canonical_url'], 'https://www.amazon.com/dp/B012345678')

    def test_international_and_gp_product(self):
        self.assertEqual(parse_amazon_url('https://amazon.in/gp/product/B012345678/')['marketplace'], 'amazon.in')

    def test_rejects_untrusted_urls(self):
        for url in ('http://amazon.com/dp/B012345678', 'https://amazon.com.evil.test/dp/B012345678',
                    'https://amazon.com@evil.test/dp/B012345678', 'https://amazon.com:8443/dp/B012345678',
                    'https://amzn.to/test', 'https://127.0.0.1/dp/B012345678', 'https://amazon.com/dp/short'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_amazon_url(url)

    def test_url_alone_is_inconclusive(self):
        response = assess_listing(AmazonAssessmentInput(url='https://amazon.com/dp/B012345678'), UnavailableModel())
        self.assertEqual(response['status'], 'inconclusive')
        self.assertIsNone(response['review_signal'])
        self.assertEqual(response['retrieval']['status'], 'unsupported')
        self.assertEqual(response['retrieval']['reviews_analyzed'], 0)

    def test_user_evidence_is_not_verified(self):
        request = AmazonAssessmentInput(url='https://amazon.com/dp/B012345678', seller='Example seller', seller_authorized='no', review_text='Example text')
        response = assess_listing(request, UnavailableModel())
        self.assertTrue(any(item['state'] == 'attention' for item in response['checks']))
        self.assertTrue(any(item['state'] == 'unavailable' for item in response['checks']))
        self.assertEqual(response['status'], 'inconclusive')

    def test_limits(self):
        with self.assertRaises(Exception):
            AmazonAssessmentInput(url='x' * 2049)
        with self.assertRaises(Exception):
            AmazonAssessmentInput(url='https://amazon.com/dp/B012345678', seller_authorized='maybe')

if __name__ == '__main__':
    unittest.main()
