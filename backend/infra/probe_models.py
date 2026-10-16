"""Prints the Gemini and embedding models available to this project/region.
Run after `gcloud auth application-default login`. Copy the IDs you pick into .env."""
import os
from google import genai

project = os.environ["GCP_PROJECT"]
region = os.environ.get("VERTEX_REGION") or os.environ["GCP_REGION"]
client = genai.Client(vertexai=True, project=project, location=region)

for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    print(f"{m.name:60} {','.join(actions)}")

print("\nPick a GA Gemini Flash model for GEMINI_MODEL and a text-embedding model "
      "for EMBED_MODEL. Record the region you used in README.md.")
