import copy
import os
import unittest
from unittest.mock import Mock, patch

from jev_relations import JevRelationEvaluator, JevError, QUESTIONS


class JevTests(unittest.TestCase):
    def setUp(self):
        self.a = {"@id": "Email/a", "archive": "synthetic", "subject": "Test", "body": "Project A meeting"}
        self.b = dict(self.a, **{"@id": "Email/b", "body": "Project A follow-up"})
        self.response = {"model": "jev-test-version", "answers": {
            name: {"type": "noul", "noul": 0.8} for name in QUESTIONS}}
        self.transport = Mock(return_value=self.response)
        self.evaluator = JevRelationEvaluator(enabled=True, transport=self.transport)
        self.env = patch.dict(os.environ, {"TYPESAFE_API_KEY": "synthetic-test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_valid_multiple_relations_remain_unreviewed(self):
        first = self.evaluator.evaluate(self.a, self.b)
        second = self.evaluator.evaluate(self.a, self.b)
        self.assertEqual(len(first), 3)
        self.assertEqual([x['id'] for x in first], [x['id'] for x in second])
        self.assertTrue(all(x['status'] == 'unreviewed' for x in first))
        payload = self.transport.call_args.args[0]
        self.assertEqual(payload['state']['email_a']['body'], self.a['body'])
        self.assertNotIn('synthetic-test-key', str(first))

    def test_disabled_without_network(self):
        with self.assertRaises(JevError):
            JevRelationEvaluator(transport=self.transport).evaluate(self.a, self.b)
        self.transport.assert_not_called()

    def test_missing_key(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            with self.assertRaises(JevError):
                self.evaluator.evaluate(self.a, self.b)
        self.transport.assert_not_called()

    def test_input_guards(self):
        for b in (self.a, dict(self.b, archive='other'), dict(self.b, body=None), dict(self.b, body='x'*25000)):
            with self.subTest(b_id=b['@id']), self.assertRaises(ValueError):
                self.evaluator.evaluate(self.a, b)
        self.transport.assert_not_called()

    def test_reject_invalid_probabilities(self):
        for value in (True, -1, 1.1, float('nan'), float('inf'), '0.9', None):
            response = copy.deepcopy(self.response)
            response['answers']['same_project']['noul'] = value
            self.transport.return_value = response
            with self.subTest(value=value), self.assertRaises(JevError):
                self.evaluator.evaluate(self.a, self.b)

    def test_malformed_responses(self):
        for response in ({}, None, {'model':'x', 'answers':{}}, {'model':'x', 'answers':dict.fromkeys(QUESTIONS, {})}):
            self.transport.return_value = response
            with self.assertRaises(JevError):
                self.evaluator.evaluate(self.a, self.b)

    def test_changed_input_changes_provenance(self):
        first = self.evaluator.evaluate(self.a, self.b)
        second = self.evaluator.evaluate(self.a, dict(self.b, subject='Changed'))
        self.assertNotEqual(first[0]['id'], second[0]['id'])
