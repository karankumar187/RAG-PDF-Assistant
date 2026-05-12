import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType, MatchText


class QdrantStorage:
    def __init__(self, collection="docs", dim=1536):
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)
        self.collection = collection
        if self.client.collection_exists(self.collection):
            # Check if the existing collection has the right vector size
            info = self.client.get_collection(self.collection)
            existing_dim = info.config.params.vectors.size
            if existing_dim != dim:
                # Dimension mismatch — recreate collection
                self.client.delete_collection(self.collection)
                self._create_collection(dim)
        else:
            self._create_collection(dim)
        # Always ensure the payload index exists
        self._ensure_index()

    def _create_collection(self, dim):
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    def _ensure_index(self):
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="user_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

    def upsert(self, ids, vectors, payloads):
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(self.collection, points=points)

    def search(self, query_vector, top_k: int = 5, source_id: str = None, user_prefix: str = None):
        """Search with optional exact source_id filter or user_prefix filter."""
        query_filter = None
        if source_id:
            # Exact match — user querying a specific file
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_id)
                    )
                ]
            )
        elif user_prefix:
            # Query all docs belonging to this user exactly
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_prefix)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=top_k
        ).points
        contexts = []
        sources = set()

        for r in results:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources)}

    def list_sources(self, user_prefix: str) -> list[str]:
        """Return unique source names belonging to a user (prefix match)."""
        sources = set()
        next_offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_prefix)
                        )
                    ]
                ) if user_prefix else None,
                with_payload=["source"],
                limit=100,
                offset=next_offset,
            )
            for r in records:
                payload = getattr(r, "payload", None) or {}
                s = payload.get("source", "")
                if s:
                    sources.add(s)
            if next_offset is None:
                break
        return sorted(sources)

    def delete_by_source(self, source_id: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_id)
                    )
                ]
            )
        )