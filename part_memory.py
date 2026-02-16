"""
Part Memory – vector-backed context graph for SolidWorks parts.

Each SolidWorks part gets a Qdrant *collection*.  Every feature operation
(sketch, extrude, fillet, …) is stored as a *point* in that collection with:
  - an embedding (generated locally by Nomic Embed via Ollama)
  - a rich payload (feature type, parameters, user intent, timestamp, label)

This gives each part a "memory graph" that can be queried later so that
Claude has full context when the user wants to modify or extend the part.

Requirements:
  - Qdrant running locally (default http://localhost:6333)
  - Ollama running locally with the nomic-embed-text model pulled
    (``ollama pull nomic-embed-text``)
"""

import time
import uuid
from datetime import datetime, timezone

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

# ---------------------------------------------------------------------------
# Config defaults (overridable via init)
# ---------------------------------------------------------------------------
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768  # nomic-embed-text outputs 768-d vectors


class PartMemory:
    """Vector-backed memory store for a single SolidWorks part."""

    def __init__(
        self,
        part_name: str,
        qdrant_url: str = DEFAULT_QDRANT_URL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
    ):
        self.part_name = part_name
        # Sanitise the collection name (Qdrant allows alphanumeric + _ -)
        self.collection = _safe_collection_name(part_name)
        self.qdrant = QdrantClient(url=qdrant_url)
        self.ollama_url = ollama_url.rstrip("/")
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------
    def _ensure_collection(self):
        """Create the Qdrant collection for this part if it doesn't exist."""
        existing = [c.name for c in self.qdrant.get_collections().collections]
        if self.collection not in existing:
            self.qdrant.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM, distance=Distance.COSINE
                ),
            )

    # ------------------------------------------------------------------
    # Embedding via Ollama (local nomic-embed-text)
    # ------------------------------------------------------------------
    def _embed(self, text: str) -> list[float]:
        """Get an embedding vector from Ollama's nomic-embed-text model."""
        resp = httpx.post(
            f"{self.ollama_url}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"][0]

    # ------------------------------------------------------------------
    # Store a feature event
    # ------------------------------------------------------------------
    def record_feature(
        self,
        feature_type: str,
        label: str,
        user_intent: str,
        parameters: dict,
        extra: dict | None = None,
    ) -> str:
        """Record a feature operation into the part's memory.

        Args:
            feature_type: e.g. "sketch_rectangle", "extrude", "fillet"
            label: human-readable label assigned to this feature in SolidWorks
            user_intent: the raw voice command / text that triggered this
            parameters: dict of numeric or string params used
            extra: any additional metadata

        Returns:
            The UUID of the stored point.
        """
        description = (
            f"{feature_type}: {label}. "
            f"Intent: {user_intent}. "
            f"Params: {parameters}"
        )
        vector = self._embed(description)

        point_id = str(uuid.uuid4())
        payload = {
            "feature_type": feature_type,
            "label": label,
            "user_intent": user_intent,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": description,
        }
        if extra:
            payload.update(extra)

        self.qdrant.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(id=point_id, vector=vector, payload=payload)
            ],
        )
        return point_id

    # ------------------------------------------------------------------
    # Query / recall
    # ------------------------------------------------------------------
    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve the most relevant past feature events for a query.

        Args:
            query: natural-language description of what the user wants
            top_k: max number of results

        Returns:
            List of payload dicts ordered by relevance.
        """
        vector = self._embed(query)
        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
        )
        return [hit.payload for hit in results.points]

    def get_full_history(self) -> list[dict]:
        """Return every feature event stored for this part, ordered by time."""
        # Scroll through all points
        records, _next = self.qdrant.scroll(
            collection_name=self.collection,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )
        items = [r.payload for r in records]
        items.sort(key=lambda p: p.get("timestamp", ""))
        return items

    def build_context_summary(self, query: str = "") -> str:
        """Build a text summary of this part's history for injection into
        a Claude prompt.  If *query* is given, the most relevant events
        are listed first; otherwise the full chronological history is used.
        """
        if query:
            events = self.recall(query, top_k=10)
        else:
            events = self.get_full_history()

        if not events:
            return "No prior features recorded for this part."

        lines = [f"## Feature history for part '{self.part_name}'\n"]
        for i, ev in enumerate(events, 1):
            lines.append(
                f"{i}. [{ev.get('feature_type')}] \"{ev.get('label')}\" – "
                f"{ev.get('user_intent')} (params: {ev.get('parameters')}, "
                f"time: {ev.get('timestamp')})"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_collection_name(name: str) -> str:
    """Convert an arbitrary part name into a valid Qdrant collection name."""
    safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in name)
    return f"sw_part_{safe}"[:128]
