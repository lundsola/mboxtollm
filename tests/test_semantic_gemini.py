import os
import unittest
from unittest.mock import patch
from gemini_encoder import GeminiEncoder
from semantic_search import SemanticIndex, chunks


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'GEMINI_API_KEY': 'synthetic-test-key'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = []

    def transport(self, payload):
        self.calls.append(payload)
        return {'embedding': {'values': [1.0] + [0.0] * 767}}

    def encoder(self):
        return GeminiEncoder(enabled=True, transport=self.transport)

    def test_requires_opt_in_and_key(self):
        with self.assertRaises(ValueError):
            GeminiEncoder()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                self.encoder()

    def test_independent_vectors_and_formats(self):
        encoder = self.encoder()
        self.assertEqual(len(encoder.encode(['subject', 'body'])), 2)
        encoder.encode_query(['question'])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.calls[0]['content']['parts'], [{'text': 'title: none | text: subject'}])
        self.assertEqual(self.calls[2]['content']['parts'], [{'text': 'task: search result | query: question'}])
        self.assertNotIn('taskType', self.calls[0])
        self.assertEqual(self.calls[0]['outputDimensionality'], 768)

    def test_unicode_chunks_and_rejection(self):
        encoder = self.encoder()
        text = 'å😀' * 600
        spans = list(chunks(text, encoder))
        self.assertEqual(''.join(s[2] for s in spans), text)
        self.assertTrue(all(encoder.fits(s[2]) for s in spans))
        with self.assertRaises(ValueError):
            encoder.encode_query([text])
        self.assertEqual(self.calls, [])

    def test_invalid_response_and_redacted_error(self):
        for values in ([], [0.0]*768, [True]*768, [float('nan')]*768):
            encoder = GeminiEncoder(enabled=True, transport=lambda p: {'embedding': {'values': values}})
            with self.assertRaises(RuntimeError):
                encoder.encode(['synthetic'])
        def fail(payload):
            raise ValueError('private text synthetic-test-key')
        with self.assertRaises(RuntimeError) as error:
            GeminiEncoder(enabled=True, transport=fail).encode(['synthetic'])
        self.assertNotIn('private', str(error.exception))
        self.assertIsNone(error.exception.__cause__)

    def test_index_uses_query_format_and_rolls_back(self):
        encoder = self.encoder()
        index = SemanticIndex(':memory:', encoder)
        self.addCleanup(index.close)
        doc = {'@id':'Email/test', 'archive':'pilot', 'subject':'subject', 'body':'body'}
        index.index(doc)
        self.assertEqual(len(index.search('question', 'pilot')), 1)
        self.assertTrue(self.calls[-1]['content']['parts'][0]['text'].startswith('task: search result'))
        encoder.transport = lambda p: {}
        with self.assertRaises(RuntimeError):
            index.index(dict(doc, body='changed'))
        self.assertEqual(index.db.execute('SELECT text FROM vectors ORDER BY field').fetchall(), [('body',), ('subject',)])


if __name__ == '__main__':
    unittest.main()
