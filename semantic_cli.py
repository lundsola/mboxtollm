"""Explicit pilot commands; no implicit schema migration or external evaluation."""
import argparse
import json
import os
from semantic_search import LocalEncoder, SemanticIndex, RetrievalTools
from terminus_store import TerminusEmailStore
from relation_store import AssessmentStore
from jev_relations import JevRelationEvaluator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--index',required=True,help='Derived SQLite index path; protect like email data')
    parser.add_argument('--embedding-provider',choices=['local','gemini'],default='local')
    parser.add_argument('--allow-google',action='store_true',help='Approve sending indexed content and search queries to Google')
    parser.add_argument('--model-path',help='Preinstalled local SentenceTransformer model')
    parser.add_argument('--model-revision',help='Immutable revision used to install the local model')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('index')
    search = sub.add_parser('search')
    search.add_argument('query')
    search.add_argument('-k',type=int,default=10)
    candidates = sub.add_parser('candidates')
    candidates.add_argument('email_id')
    sub.add_parser('init-assessment-schema')
    assess = sub.add_parser('assess')
    assess.add_argument('email_id')
    assess.add_argument('--allow-external',action='store_true',help='Approve sending selected subject/body content to TypeSafe')
    assess.add_argument('--max-pairs',type=int,default=5)
    args = parser.parse_args()
    if args.command == 'assess' and not args.allow_external:
        parser.error('assess requires --allow-external; mail will be sent to TypeSafe')
    if args.embedding_provider == 'gemini':
        if not args.allow_google:
            parser.error('Gemini requires --allow-google; content and queries leave this machine')
        from gemini_encoder import GeminiEncoder
        encoder = GeminiEncoder(enabled=True)
    else:
        if not args.model_path or not args.model_revision:
            parser.error('Local embeddings require --model-path and --model-revision')
        encoder = LocalEncoder(args.model_path,args.model_revision)
    index = SemanticIndex(args.index,encoder)
    try:
        if args.command == 'search':
            print(json.dumps(index.search(args.query,args.archive,args.k),ensure_ascii=False))
            return
        from terminusdb_client import Client
        client = Client(os.environ.get('TERMINUSDB_URL','http://localhost:6363'))
        client.connect(db=os.environ['TERMINUSDB_DATABASE'],key=os.environ['TERMINUSDB_KEY'],
                       user=os.environ.get('TERMINUSDB_USER','admin'),team=os.environ.get('TERMINUSDB_TEAM','admin'))
        tools = RetrievalTools(index,TerminusEmailStore(client),args.archive)
        assessments = AssessmentStore(client)
        if args.command == 'index':
            count = 0
            for doc in client.query_document({'@type':'Email','archive':args.archive}):
                index.index(doc)
                count += 1
            print(json.dumps({'indexed':count}))
        elif args.command == 'candidates':
            print(json.dumps(tools.candidates(args.email_id),ensure_ascii=False))
        elif args.command == 'init-assessment-schema':
            assessments.install_schema()
        else:
            result = tools.assess_candidates(args.email_id,JevRelationEvaluator(enabled=True),assessments,args.max_pairs)
            print(json.dumps(result,ensure_ascii=False))
    finally:
        index.close()


if __name__ == '__main__':
    main()
