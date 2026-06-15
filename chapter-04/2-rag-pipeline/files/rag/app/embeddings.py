"""Embedding providers.

`local` uses fastembed (a small CPU model, no credentials) and is the default
so the lab runs anywhere. `bedrock` uses Amazon Titan embeddings.

Both expose the same tiny interface: `.embed(texts) -> list[list[float]]` and
`.dimension`. The vector store reads `.dimension` to size its column, so the
two stay in sync automatically.
"""
from __future__ import annotations

import json
from typing import Protocol

from .settings import Settings


class Embedder(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    """fastembed — runs on CPU, downloads a ~100MB model on first use."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)
        # Probe the output dimension once.
        probe = next(iter(self._model.embed(["dimension probe"])))
        self.dimension = len(probe)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]


class BedrockEmbedder:
    """Amazon Titan Text Embeddings v2 via the Bedrock Runtime API."""

    def __init__(self, model_id: str, region: str):
        import boto3

        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self.dimension = 1024  # Titan v2 default

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            resp = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps({"inputText": text}),
            )
            payload = json.loads(resp["body"].read())
            out.append(payload["embedding"])
        return out


def get_embedder(settings: Settings) -> Embedder:
    if settings.embeddings_provider == "bedrock":
        return BedrockEmbedder(settings.bedrock_embed_model, settings.aws_region)
    return LocalEmbedder(settings.local_embed_model)
