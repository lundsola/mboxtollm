import os
import tempfile
import unittest
from unittest.mock import patch

from semantic_search import SemanticIndex, RetrievalTools, chunks
from relation_store import AssessmentStore
from jev_relations import JevRelationEvaluator, QUESTIONS
from terminus_store import TerminusEmailStore
from tests.test_terminus_store import MemoryClient


class FakeEncoder:
    identity = 'synthetic-v1'

    def fits(self, text):
        return len(text) <= 80

    def encode(self, texts):
        return [[1+text.lower().count('budget'), 1+text.lower().count('hockey'), 1] for text in texts]


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = self.tmp.name+'/index.sqlite'
        self.encoder = FakeEncoder()
        self.index = SemanticIndex(self.path, self.encoder)
        self.addCleanup(self.index.close)
        self.client = MemoryClient()
        self.docs = [dict(**{'@type':'Email', '@id': 'Email/'+str(i)}, archive='pilot',
                          subject=subject, body=body, message_id=str(i), references=[])
                     for i,subject,body in [(1,'budget budget','hockey'), (2,'hockey','budget budget'), (3,'hockey','hockey')]]
        for doc in self.docs:
            self.index.index(doc)
        self.client.replace_document(self.docs, create=True)
        self.tools = RetrievalTools(self.index, TerminusEmailStore(self.client), 'pilot')

    def test_field_weighting(self):
        self.assertEqual(self.index.search('budget','pilot',subject_weight=1)[0]['email_id'], 'Email/1')
        self.assertEqual(self.index.search('budget','pilot',subject_weight=0)[0]['email_id'], 'Email/2')

    def test_lossless_chunking(self):
        text = 'budget åäö '*200
        parts = list(chunks(text, self.encoder))
        self.assertEqual(''.join(p[2] for p in parts), text)
        for start,end,part in parts:
            self.assertEqual(text[start:end],part)
            self.assertTrue(self.encoder.fits(part))

    def test_reindex_no_duplicate_or_stale_chunks(self):
        doc = dict(self.docs[0],body='budget '*50)
        self.index.index(doc)
        self.index.index(self.docs[0])
        count = self.index.db.execute('SELECT count(*) FROM vectors WHERE email_id=?',('Email/1',)).fetchone()[0]
        self.assertEqual(count,2)

    def test_isolation_and_limits(self):
        self.assertEqual(self.index.search('budget','other'),[])
        with self.assertRaises(ValueError): self.tools.read_email('missing')
        with self.assertRaises(ValueError): self.index.search('budget','pilot',k=101)
        with self.assertRaises(ValueError): self.index.search('x'*100,'pilot')

    def test_model_mismatch(self):
        other = FakeEncoder()
        other.identity = 'another-model'
        with self.assertRaises(ValueError): SemanticIndex(self.path,other)

    def test_reindex_rollback(self):
        before = self.index.search('budget','pilot')
        with patch.object(self.encoder,'encode',return_value=[[float('nan')]]):
            with self.assertRaises(ValueError): self.index.index(self.docs[0])
        self.assertEqual(before,self.index.search('budget','pilot'))

    def test_candidate_budget(self):
        hits = self.tools.candidates('Email/1',1)
        self.assertEqual(len(hits),1)
        self.assertNotEqual(hits[0]['email_id'],'Email/1')

    def test_end_to_end_assessments(self):
        calls = []
        def transport(payload,key,timeout):
            calls.append(payload)
            return {'model':'jev-synthetic', 'answers':{q:{'type':'noul','noul':0.8} for q in QUESTIONS}}
        evaluator = JevRelationEvaluator(enabled=True,transport=transport)
        store = AssessmentStore(self.client)
        with patch.dict(os.environ,{'TYPESAFE_API_KEY':'fake-test-key'}):
            records = self.tools.assess_candidates('Email/1',evaluator,store,max_pairs=1)
            self.tools.assess_candidates('Email/1',evaluator,store,max_pairs=1)
        self.assertEqual(len(calls),2)
        self.assertEqual(len(list(store.list_for_archive('pilot'))),3)
        self.assertTrue(all(r['status']=='unreviewed' for r in records))
        bad = dict(records[0],archive='other')
        with self.assertRaises(ValueError): store.save([bad])
        with self.assertRaises(ValueError): store.save([dict(records[0],status='accepted')])

    def test_persistent_reopen(self):
        another = SemanticIndex(self.path,self.encoder)
        try:
            self.assertEqual(another.search('budget','pilot'),self.index.search('budget','pilot'))
        finally:
            another.close()
