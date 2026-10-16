"""Creates the Vertex AI RAG Engine corpus from data/docs and proves it answers.
Run once per project:  python -m infra.build_rag

Uses the `agentplatform` client rather than `vertexai.rag`: the installed SDK
(google-cloud-aiplatform) marks `vertexai.rag` as deprecated and points at
`agentplatform` as the replacement. `agentplatform.init` is the same function
object as `vertexai.init` (both are `google.cloud.aiplatform.init`), and
`agentplatform.rag` exposes the identical call shape (create_corpus,
import_files, retrieval_query, RagResource, RagVectorDbConfig, ...) without
emitting the deprecation warning. Confined to this file and the
`agent.tools.doc_search` vertex path so the test suite — run with warnings
as errors — never imports it.
"""
import os
import re
from pathlib import Path

import agentplatform
from agentplatform import rag
from google.cloud import storage

PROJECT = os.environ["GCP_PROJECT"]
REGION = os.environ.get("VERTEX_REGION") or os.environ["GCP_REGION"]
BUCKET = os.environ["GCS_BUCKET"]
DOCS = Path(__file__).resolve().parents[1] / "data" / "docs"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

agentplatform.init(project=PROJECT, location=REGION)

# The RAG Engine corpus reads its source files from GCS regardless of this
# project's FILES_BACKEND selector (which governs the app's own file storage,
# default "local"), so this upload always goes straight to the bucket via the
# storage client rather than through agent.tools.storage.put_bytes.
bucket = storage.Client(project=PROJECT).bucket(BUCKET)
uris = []
for path in sorted(DOCS.glob("*.md")):
    bucket.blob(f"docs/{path.name}").upload_from_string(
        path.read_bytes(), content_type="text/markdown")
    uris.append(f"gs://{BUCKET}/docs/{path.name}")
    print("uploaded", path.name)

DISPLAY_NAME = "quality-docs"
corpus = next((c for c in rag.list_corpora() if c.display_name == DISPLAY_NAME), None)
if corpus is not None:
    print(f"reusing existing corpus {corpus.name}")
else:
    corpus = rag.create_corpus(
        display_name=DISPLAY_NAME,
        backend_config=rag.RagVectorDbConfig(
            rag_embedding_model_config=rag.RagEmbeddingModelConfig(
                vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                    publisher_model=f"publishers/google/models/{os.environ['EMBED_MODEL']}"))))
    print(f"created corpus {corpus.name}")

if list(rag.list_files(corpus.name)):
    print("corpus already has imported files, skipping import_files")
else:
    rag.import_files(corpus.name, uris, transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=64)))
    print("imported", len(uris), "files")

print(f"\nRAG_CORPUS={corpus.name}   <- put this in .env\n")

if ENV_FILE.exists():
    text = ENV_FILE.read_text()
    new_line = f"RAG_CORPUS={corpus.name}"
    if re.search(r"^RAG_CORPUS=.*$", text, flags=re.M):
        text = re.sub(r"^RAG_CORPUS=.*$", new_line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{new_line}\n"
    ENV_FILE.write_text(text)
    print(f"wrote {new_line} to {ENV_FILE}")

resp = rag.retrieval_query(rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
                           text="solder bridging caused by reflow peak temperature "
                                "above the profile limit",
                           rag_retrieval_config=rag.RagRetrievalConfig(top_k=3))
for ctx in resp.contexts.contexts:
    print(f"- {getattr(ctx, 'source_uri', '?')}: {(ctx.text or '')[:160]}")

joined = " ".join(c.text or "" for c in resp.contexts.contexts)
assert "Solder bridging" in joined and "Row 14" in joined, \
    "corpus does not return PFMEA row 14 — check chunk size and document headings"
print("\nPhase 2 gate passed: test query returns PFMEA row 14 with its source.")
