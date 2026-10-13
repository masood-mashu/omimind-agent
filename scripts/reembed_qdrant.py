"""Re-embed existing Qdrant memories with the configured FastEmbed model.

The migration keeps every point ID and payload. It computes all replacement
vectors before writing, and restores the original vectors if the update or its
verification fails during this process.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointVectors

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.embeddings.fastembed import FastEmbedEmbedding
from backend.config import settings


def _collect_points(client: QdrantClient) -> list[Any]:
    points = []
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=settings.collection_name,
            offset=offset,
            limit=128,
            with_payload=True,
            with_vectors=True,
        )
        points.extend(batch)
        if offset is None:
            return points


def _vector_list(value: Any) -> list[float]:
    if isinstance(value, dict):
        if len(value) != 1:
            raise ValueError("Expected one dense vector per memory point.")
        value = next(iter(value.values()))
    if not isinstance(value, list) or not value:
        raise ValueError("A memory point is missing its current vector.")
    return [float(item) for item in value]


def _update(client: QdrantClient, rows: list[tuple[int | str, list[float]]]) -> None:
    if rows:
        client.update_vectors(
            collection_name=settings.collection_name,
            points=[PointVectors(id=point_id, vector=vector) for point_id, vector in rows],
            wait=True,
        )


def _verify_sample(client: QdrantClient, rows: list[tuple[int | str, list[float]]]) -> None:
    sample = rows[: min(5, len(rows))]
    points = client.retrieve(
        collection_name=settings.collection_name,
        ids=[point_id for point_id, _ in sample],
        with_payload=False,
        with_vectors=True,
    )
    expected = dict(sample)
    if len(points) != len(sample):
        raise RuntimeError("Post-update point verification was incomplete.")
    for point in points:
        actual = _vector_list(point.vector)
        target = expected[point.id]
        if len(actual) != 384 or any(
            abs(left - right) > 1e-5 for left, right in zip(actual, target, strict=True)
        ):
            raise RuntimeError("Post-update vector verification failed.")


def _apply_and_verify(
    client: QdrantClient,
    originals: list[tuple[int | str, list[float]]],
    replacements: list[tuple[int | str, list[float]]],
) -> None:
    try:
        _update(client, replacements)
        _verify_sample(client, replacements)
    except Exception:
        try:
            _update(client, originals)
        except Exception as rollback_error:
            raise RuntimeError(
                "Re-embedding failed and automatic rollback also failed; inspect the collection immediately."
            ) from rollback_error
        raise


def reembed(*, apply: bool) -> int:
    if not settings.qdrant_url or not settings.qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be configured.")

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)
    points = _collect_points(client)
    originals: list[tuple[int | str, list[float]]] = []
    texts: list[str] = []
    for point in points:
        payload = point.payload or {}
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError(f"Point {point.id} has no text; refusing a partial re-embed.")
        speaker = str(payload.get("speaker") or "Speaker")
        texts.append(f"{speaker} {text}")
        originals.append((point.id, _vector_list(point.vector)))

    embedder = FastEmbedEmbedding()
    replacements = embedder.embed_batch(texts)
    if len(replacements) != len(points) or any(len(vector) != 384 for vector in replacements):
        raise RuntimeError("FastEmbed returned an incomplete or incorrectly sized vector set.")

    print(f"Collection: {settings.collection_name}")
    print(f"Points ready: {len(points)}")
    print(f"Embedding model: {embedder.model_name} (384 dimensions)")
    if not apply:
        print("Dry run only. Re-run with --apply to update vectors.")
        return len(points)

    replacement_rows = [(point.id, vector) for point, vector in zip(points, replacements, strict=True)]
    _apply_and_verify(client, originals, replacement_rows)

    print(f"Updated and verified: {len(points)} points. Payloads and IDs were preserved.")
    return len(points)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Replace stored vectors after all points are preflighted and embedded.",
    )
    args = parser.parse_args()
    try:
        reembed(apply=args.apply)
    except Exception as exc:
        print(f"Re-embedding failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
