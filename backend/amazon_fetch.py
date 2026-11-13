"""Best-effort retrieval of public Amazon India listing content.

Requests are limited to a canonical, validated ASIN URL. No authentication,
redirects, access-control bypass, or fabricated data is used.
"""
import html
import json
import re
import socket
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener

MAX_BYTES = 8_000_000
MAX_REVIEWS = 10
ASIN = re.compile(r"^[A-Z0-9]{10}$")

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.reviews = []
        self._depth = 0
        self._capture = None
        self._capture_depth = 0
        self._parts = []
        self._json = False
        self._json_parts = []
        self.metadata = {}
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        self._depth += 1
        attrs = dict(attrs)
        if tag in ('style', 'script'):
            self._ignored += 1
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key and attrs.get('content'):
                self.metadata[key] = attrs['content'][:1000]
        if self._capture is None:
            if attrs.get('id') == 'productTitle':
                self._capture = 'title'
            elif attrs.get('data-hook') in ('review-body', 'review-collapsed'):
                self._capture = 'review'
            if self._capture:
                self._capture_depth = self._depth
                self._parts = []
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json':
            self._json = True
            self._json_parts = []
        # HTML void elements have no closing tags.
        if tag in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self._depth -= 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self._capture and not self._ignored:
            self._parts.append(data)
        if self._json:
            self._json_parts.append(data)

    def handle_endtag(self, tag):
        if tag in ('style', 'script') and self._ignored:
            self._ignored -= 1
        if self._json and tag == 'script':
            self._json = False
            try:
                self._read_structured(json.loads(''.join(self._json_parts)))
            except (ValueError, TypeError, RecursionError):
                pass
        if self._capture and self._depth == self._capture_depth:
            text = ' '.join(''.join(self._parts).split())[:10000]
            if text:
                if self._capture == 'title':
                    self.title = text[:500]
                elif len(self.reviews) < MAX_REVIEWS:
                    self.reviews.append(text)
            self._capture = None
        self._depth = max(0, self._depth - 1)

    def _read_structured(self, value):
        if isinstance(value, list):
            for item in value[:100]:
                self._read_structured(item)
        elif isinstance(value, dict):
            typ = value.get('@type', '')
            if typ == 'Product' or (isinstance(typ, list) and 'Product' in typ):
                name = value.get('name')
                if isinstance(name, str) and not self.title:
                    self.title = name[:500]
                review = value.get('review', [])
                for item in review if isinstance(review, list) else [review]:
                    if isinstance(item, dict) and isinstance(item.get('reviewBody'), str):
                        text = ' '.join(item['reviewBody'].split())[:10000]
                        if text and len(self.reviews) < MAX_REVIEWS:
                            self.reviews.append(text)
            graph = value.get('@graph')
            if isinstance(graph, list):
                self._read_structured(graph)


def fetch_listing(marketplace, asin, opener=None):
    if marketplace != 'amazon.in':
        return {'status': 'unsupported', 'message': 'Automatic retrieval currently supports Amazon India only.', 'reviews': []}
    if not ASIN.fullmatch(asin):
        raise ValueError('Invalid product ID')
    url = f'https://www.amazon.in/dp/{asin}'
    request = Request(url, headers={'User-Agent': 'ReviewLens/1.0 (local review analysis)', 'Accept': 'text/html'})
    try:
        with (opener or build_opener(NoRedirect())).open(request, timeout=8) as response:
            if response.geturl() != url:
                return {'status': 'unavailable', 'message': 'The listing redirected; redirects are not followed.', 'reviews': []}
            content_type = response.headers.get_content_type()
            if content_type not in ('text/html', 'application/xhtml+xml'):
                return {'status': 'unavailable', 'message': 'Amazon did not return an HTML listing.', 'reviews': []}
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return {'status': 'unavailable', 'message': 'The listing response exceeded the size limit.', 'reviews': []}
            charset = response.headers.get_content_charset() or 'utf-8'
            try:
                body = data.decode(charset, errors='replace')
            except LookupError:
                body = data.decode('utf-8', errors='replace')
    except HTTPError as exc:
        return {'status': 'unavailable', 'message': f'Amazon returned HTTP {exc.code}; listing access was not available.', 'reviews': []}
    except (URLError, TimeoutError, socket.timeout, OSError):
        return {'status': 'unavailable', 'message': 'Could not access the Amazon listing. Check your connection or paste review text manually.', 'reviews': []}
    if re.search(r'captcha|robot check|enter the characters you see below', body, re.I):
        return {'status': 'unavailable', 'message': 'Amazon requested a verification step; automated access was not attempted.', 'reviews': []}
    parser = ListingParser()
    try:
        parser.feed(body)
    except (ValueError, RecursionError):
        return {'status': 'unavailable', 'message': 'The listing response could not be parsed.', 'reviews': []}
    title = parser.metadata.get('og:title', '')[:500] or parser.title
    reviews = list(dict.fromkeys(parser.reviews))[:MAX_REVIEWS]
    if not title and not reviews:
        return {'status': 'unavailable', 'message': 'No recognizable product details or review text were available.', 'reviews': []}
    return {'status': 'retrieved', 'message': 'Public listing content retrieved.' if reviews else 'Product details were retrieved, but no review text was available on the page.', 'title': html.unescape(title), 'reviews': reviews, 'source': url}
