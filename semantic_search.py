"""Persistent exact-vector pilot; derived index, not authoritative mail storage."""
import hashlib
import json
import math
import sqlite3


def unit(vector):
    values = [float(v) for v in vector]
    norm = math.sqrt(sum(v*v for v in values))
    if not values or not math.isfinite(norm) or norm == 0:
        raise ValueError('Invalid embedding')
    return [v/norm for v in values]


class LocalEncoder:
    """Only uses a preinstalled model: never downloads weights automatically."""
    def __init__(self, model_path, revision):
        if not revision:
            raise ValueError('An immutable model revision is required')
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_path, local_files_only=True)
        self.identity = f'{model_path}:{revision}:plain-encode-v1'

    def fits(self, text):
        return len(self.model.tokenizer.encode(text)) <= self.model.max_seq_length

    def encode(self, texts):
        if any(not self.fits(t) for t in texts):
            raise ValueError('Input exceeds embedding token budget')
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


def chunks(text, encoder, start=0):
    """Lossless character spans, recursively split to avoid token truncation."""
    if not text.strip():
        return
    if len(text) <= 1000 and encoder.fits(text):
        yield start, start+len(text), text
    elif len(text) < 2:
        raise ValueError('Cannot fit text into embedding model')
    else:
        middle = len(text)//2
        yield from chunks(text[:middle], encoder, start)
        yield from chunks(text[middle:], encoder, start+middle)


class SemanticIndex:
    def __init__(self, path, encoder):
        self.encoder = encoder
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS vectors (archive TEXT, email_id TEXT, field TEXT, start INTEGER, end INTEGER, text TEXT, vector TEXT, source_hash TEXT)')
        identity = encoder.identity + ':char-split-1000-v1'
        old = self.db.execute("SELECT value FROM config WHERE key='identity'").fetchone()
        if old and old[0] != identity:
            self.db.close()
            raise ValueError('Embedding configuration mismatch: build a separate index')
        self.db.execute("INSERT OR IGNORE INTO config VALUES ('identity', ?)", (identity,))
        self.db.commit()

    def close(self):
        self.db.close()

    def index(self, email):
        for name in ('archive', '@id', 'subject', 'body'):
            if not isinstance(email.get(name), str):
                raise ValueError('Missing email field: '+name)
        source_hash = hashlib.sha256(json.dumps([email['subject'], email['body']], ensure_ascii=False).encode()).hexdigest()
        # One email per transaction: failed reindex leaves the prior version intact.
        with self.db:
            self.db.execute('DELETE FROM vectors WHERE archive=? AND email_id=?', (email['archive'], email['@id']))
            for field in ('subject', 'body'):
                for start, end, text in chunks(email[field], self.encoder):
                    encoded = self.encoder.encode([text])
                    if len(encoded) != 1:
                        raise ValueError('Embedding count mismatch')
                    vector = unit(encoded[0])
                    dimension = self.db.execute("SELECT value FROM config WHERE key='dimension'").fetchone()
                    if dimension and int(dimension[0]) != len(vector):
                        raise ValueError('Embedding dimension mismatch')
                    self.db.execute("INSERT OR IGNORE INTO config VALUES ('dimension', ?)", (str(len(vector)),))
                    self.db.execute('INSERT INTO vectors VALUES (?,?,?,?,?,?,?,?)',
                                    (email['archive'], email['@id'], field, start, end, text, json.dumps(vector), source_hash))

    def search(self, query, archive, k=10, subject_weight=0.35, exclude=None):
        if not query.strip() or not archive or not 1 <= k <= 100 or not 0 <= subject_weight <= 1:
            raise ValueError('Invalid search parameters')
        if not self.encoder.fits(query):
            raise ValueError('Query exceeds embedding token budget')
        encode_query = getattr(self.encoder, 'encode_query', self.encoder.encode)
        q = unit(encode_query([query])[0])
        hits = {}
        for mid, field, start, end, text, raw, source_hash in self.db.execute(
            'SELECT email_id,field,start,end,text,vector,source_hash FROM vectors WHERE archive=?', (archive,)
        ):
            if mid == exclude:
                continue
            vector = json.loads(raw)
            if len(q) != len(vector):
                raise ValueError('Embedding dimension mismatch')
            score = sum(a*b for a,b in zip(q, vector))
            item = hits.setdefault(mid, {'email_id': mid, 'archive': archive, 'fields': {}, 'source_hash': source_hash})
            previous = item['fields'].get(field)
            if previous is None or score > previous['similarity']:
                item['fields'][field] = {'similarity': score, 'start': start, 'end': end, 'text': text}
        for item in hits.values():
            weights = {'subject': subject_weight, 'body': 1-subject_weight}
            total = sum(weights[f] for f in item['fields'])
            item['score'] = sum(weights[f]*v['similarity'] for f,v in item['fields'].items()) / total if total else 0
        return sorted(hits.values(), key=lambda h: (-h['score'], h['email_id']))[:k]


class RetrievalTools:
    """Read-only agent-facing operations, bound to one authorized archive."""
    def __init__(self, index, store, archive):
        self.index, self.store, self.archive = index, store, archive

    def search(self, query, k=10):
        return self.index.search(query, self.archive, k)

    def read_email(self, email_id):
        docs = list(self.store.client.query_document({'@type': 'Email', '@id': email_id, 'archive': self.archive}))
        if len(docs) != 1:
            raise ValueError('Email not found in authorized archive')
        return docs[0]

    def thread(self, email_id):
        return self.store.get_thread(self.archive, self.read_email(email_id)['message_id'])

    def candidates(self, email_id, k=10):
        email = self.read_email(email_id)
        # Search both fields and all body spans; bounded output, not all mail pairs.
        found = {}
        for field in ('subject', 'body'):
            for _, _, text in chunks(email[field], self.index.encoder):
                for hit in self.index.search(text, self.archive, k, exclude=email_id):
                    if hit['email_id'] not in found or hit['score'] > found[hit['email_id']]['score']:
                        found[hit['email_id']] = hit
        return sorted(found.values(), key=lambda h: (-h['score'], h['email_id']))[:k]

    def assess_candidates(self, email_id, evaluator, assessment_store, max_pairs=5):
        if not 1 <= max_pairs <= 20:
            raise ValueError('max_pairs must be 1..20')
        source = self.read_email(email_id)
        output = []
        for hit in self.candidates(email_id, max_pairs):
            target = self.read_email(hit['email_id'])
            records = evaluator.evaluate(source, target)
            assessment_store.save(records)
            output.extend(records)
        return output
