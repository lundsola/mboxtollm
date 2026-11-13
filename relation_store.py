"""Persist assessments separately from factual relations; explicit schema setup."""
import math
from jev_relations import QUESTIONS

FIELDS = ('archive', 'relation', 'status', 'model', 'requested_model',
          'question_version', 'input_sha256', 'evaluated_at')
SCHEMA = {'@type': 'Class', '@id': 'RelationAssessment',
          'source': 'Email', 'target': 'Email', 'probability': 'xsd:double',
          **{field: 'xsd:string' for field in FIELDS}}


class AssessmentStore:
    def __init__(self, client):
        self.client = client

    def install_schema(self):
        self.client.insert_document(SCHEMA, graph_type='schema')

    def save(self, records):
        docs = []
        for record in records:
            if any(not isinstance(record.get(f), str) or not record[f] for f in (*FIELDS, 'id', 'source_id', 'target_id')):
                raise ValueError('Missing assessment provenance')
            p = record.get('probability')
            if isinstance(p, bool) or not isinstance(p, (int,float)) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError('Invalid probability')
            if record['status'] != 'unreviewed' or record['relation'] not in QUESTIONS:
                raise ValueError('Only known, unreviewed assessments can be saved')
            if record['source_id'] == record['target_id']:
                raise ValueError('Self relation')
            for mid in (record['source_id'], record['target_id']):
                matches = list(self.client.query_document({'@type':'Email', '@id':mid, 'archive':record['archive']}))
                if len(matches) != 1:
                    raise ValueError('Source email missing from archive')
            docs.append({'@id': 'RelationAssessment/'+record['id'], '@type':'RelationAssessment',
                         'source': record['source_id'], 'target': record['target_id'],
                         'probability': float(p), **{f:record[f] for f in FIELDS}})
        if docs:
            self.client.replace_document(docs, create=True)

    def list_for_archive(self, archive):
        return self.client.query_document({'@type':'RelationAssessment', 'archive':archive})
