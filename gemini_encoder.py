"""Opt-in Gemini REST embeddings; no SDK, redirects or automatic retries."""
import json
import math
import os
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GeminiEncoder:
    MODEL = 'gemini-embedding-2'
    DIMENSIONS = 768

    def __init__(self, *, enabled=False, transport=None):
        if not enabled:
            raise ValueError('Gemini requires explicit approval to send text to Google')
        self.key = os.environ.get('GEMINI_API_KEY')
        if not self.key:
            raise ValueError('Set GEMINI_API_KEY in the runtime environment')
        self.transport = transport or self._request
        self.identity = f'google:{self.MODEL}:768:retrieval-prefix-v1:utf8-1000'

    def fits(self, text):
        # Conservative byte cap, not a tokenizer estimate; leave ample room
        # for prefixes. Never silently truncate either documents or queries.
        return isinstance(text, str) and len(text.encode('utf-8')) <= 1000

    def _request(self, payload):
        request = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL}:embedContent',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': self.key},
            method='POST')
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)

    def encode(self, texts):
        return self._encode(texts, 'title: none | text: ')

    def encode_query(self, texts):
        return self._encode(texts, 'task: search result | query: ')

    def _encode(self, texts, prefix):
        texts = list(texts)
        if any(not self.fits(t) or not t.strip() for t in texts):
            raise ValueError('Empty input or Gemini input exceeds 1000 UTF-8 bytes')
        result = []
        for text in texts:
            # One request per span: Gemini 2 aggregates multi-input content.
            payload = {'model': f'models/{self.MODEL}',
                       'content': {'parts': [{'text': prefix + text}]},
                       'outputDimensionality': self.DIMENSIONS}
            try:
                values = self.transport(payload)['embedding']['values']
                if (not isinstance(values, list) or len(values) != self.DIMENSIONS
                        or any(isinstance(v, bool) or not isinstance(v, (int, float))
                               or not math.isfinite(v) for v in values)
                        or not any(values)):
                    raise ValueError('Invalid vector')
            except Exception:
                # Provider errors may contain source text or credentials.
                raise RuntimeError('Gemini embedding failed; check credentials, quota and service status') from None
            result.append(values)
        return result
