import copy
import mailbox
import os
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from terminus_store import TerminusEmailStore, iter_documents


class MemoryClient:
    def __init__(self):
        self.docs = {}

    def replace_document(self, docs, create=False):
        assert create
        self.docs.update({d['@id']: copy.deepcopy(d) for d in docs})

    def query_document(self, template):
        return [d for d in self.docs.values() if all(d.get(k) == v for k, v in template.items())]


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'sample.mbox'
        box = mailbox.mbox(self.path)
        for mid, parent in [('<root@example.test>', None), ('<reply@example.test>', '<root@example.test>'), (None, None)]:
            msg = EmailMessage()
            if mid:
                msg['Message-ID'] = mid
            if parent:
                msg['In-Reply-To'] = parent
            msg['Subject'] = 'Syntetiskt mejl'
            msg['From'] = 'sender@example.test'
            msg.set_content('Hej Ola! Fullständig text med åäö.')
            box.add(msg)
        box.close()
        self.client = MemoryClient()
        self.store = TerminusEmailStore(self.client)

    def test_repeat_import_and_thread(self):
        self.assertEqual(self.store.import_mbox(self.path, 'pilot', 1), 3)
        self.store.import_mbox(self.path, 'pilot', 2)
        self.assertEqual(len(self.client.docs), 3)
        thread = self.store.get_thread('pilot', '<reply@example.test>')
        self.assertEqual({d['message_id'] for d in thread}, {'<root@example.test>', '<reply@example.test>'})

    def test_missing_id_and_unicode_preserved(self):
        docs = list(iter_documents(self.path, 'pilot'))
        self.assertTrue(docs[-1]['message_id'].startswith('sha256:'))
        self.assertIn('åäö', docs[0]['body'])

    def test_archives_are_isolated(self):
        self.store.import_mbox(self.path, 'one')
        self.store.import_mbox(self.path, 'two')
        self.assertEqual(len(self.client.docs), 6)
        self.assertEqual(len(self.store.get_thread('one', '<root@example.test>')), 2)
        self.assertEqual(self.store.get_thread('absent', '<root@example.test>'), [])

    def test_bad_batch_size(self):
        with self.assertRaises(ValueError):
            self.store.import_mbox(self.path, 'pilot', 0)

    @unittest.skipUnless(os.environ.get('TERMINUSDB_TEST_DATABASE'), 'No dedicated test database configured')
    def test_real_database(self):
        # Explicit opt-in: must be a new, disposable, schema-enabled database.
        from terminusdb_client import Client
        client = Client(os.environ.get('TERMINUSDB_URL', 'http://localhost:6363'))
        client.connect(db=os.environ['TERMINUSDB_TEST_DATABASE'],
                       team=os.environ.get('TERMINUSDB_TEAM', 'admin'),
                       user=os.environ.get('TERMINUSDB_USER', 'admin'),
                       key=os.environ['TERMINUSDB_KEY'])
        store = TerminusEmailStore(client)
        store.install_schema()
        store.import_mbox(self.path, 'acceptance', 1)
        store.import_mbox(self.path, 'acceptance', 2)
        docs = list(client.query_document({'@type': 'Email', 'archive': 'acceptance'}))
        self.assertEqual(len(docs), 3)
        self.assertEqual(len(store.get_thread('acceptance', '<root@example.test>')), 2)
