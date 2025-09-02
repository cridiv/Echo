from __future__ import annotations
import hashlib
import chromadb
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Sequence
from sentence_transformers import SentenceTransformer
from Log.ingest import LogAgent


@dataclass
class EmbeddingConfig:
    db_path: str = "./chromadb"
    collection_name: str = "echo_logs"
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 256
    normalize_embeddings: bool = True


@dataclass
class LogRecord:
    id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class LogSource:
    def get_parsed_logs(self) -> List[Any]:
        parsed = LogAgent()
        if not isinstance(parsed, list):
            raise ValueError("LogAgent should return a list of parsed logs")
        return parsed


@dataclass
class LogExtractor:
    def _extract_text_and_metadata(self, item: Any) -> tuple[str, Dict[str, Any]]:
        if isinstance(item, str):
            return item, {}
        if isinstance(item, Dict):
            text = (
                item.get("text")
                or item.get("message")
                or item.get("error")
                or item.get("msg")
                or ""
            )
            metadata = {}

            timestamp = item.get("timestamp")
            if timestamp:
                if hasattr(timestamp, "isoformat"):
                    metadata["timestamp"] = timestamp.isoformat()
                else:
                    metadata["timestamp"] = timestamp
            if item.get("level"):
                metadata["level"] = item.get("level")
            if item.get("score") is not None:
                metadata["score"] = item.get("score")
            if item.get("source"):
                metadata["source"] = item.get("source")

            return text, metadata
        return str(item), {"original_type": type(item).__name__}

    def to_records(self, parsed_logs: Sequence[Any]) -> List[LogRecord]:
        records = []
        now_iso = datetime.now().isoformat()

        for item in parsed_logs:
            text, metadata = self._extract_text_and_metadata(item)

            if not text or not text.strip():
                continue

            record_id = hashlib.sha1(text.encode("utf-8")).hexdigest()
            metadata["processed at"] = now_iso

            records.append(LogRecord(id=record_id, text=text, metadata=metadata))

        return records


class SentenceEmbedder:
    """Handles text embedding with SentenceTransformers."""

    def __init__(self, cfg: EmbeddingConfig):
        self.model = SentenceTransformer(cfg.model_name)
        self.batch_size = cfg.batch_size
        self.normalize = cfg.normalize_embeddings

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        embeddings = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()


class ChromaVectorStore:
    """ChromaDB interface for storing and querying embeddings."""

    def __init__(self, cfg: EmbeddingConfig):
        self.client = chromadb.PersistentClient(path=cfg.db_path)
        self.collection = self.client.get_or_create_collection(cfg.collection_name)
        self.collection_name = cfg.collection_name

    def add(self, records: Sequence[LogRecord], embeddings: Sequence[Sequence[float]]):
        """Store records and embeddings in ChromaDB."""
        if not records:
            return

        if len(records) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(records)} records, {len(embeddings)} embeddings"
            )

        self.collection.add(
            ids=[r.id for r in records],
            documents=[r.text for r in records],
            metadatas=[r.metadata for r in records],
            embeddings=[list(vec) for vec in embeddings],
        )

    def search(
        self, query_embedding: List[float], n_results: int = 5
    ) -> Dict[str, Any]:
        """Search for similar logs using query embedding."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )


class LogEmbeddingPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, cfg: EmbeddingConfig = None):
        """Initialize pipeline with optional config."""
        self.cfg = cfg or EmbeddingConfig()
        self.source = LogSource()
        self.extractor = LogExtractor()
        self.embedder = SentenceEmbedder(self.cfg)
        self.store = ChromaVectorStore(self.cfg)

    def run(self) -> int:
        """Execute the complete pipeline."""
        # Get and validate logs
        print("Getting logs from LogAgent...")
        raw_logs = self.source.get_parsed_logs()
        if not raw_logs:
            print("No logs found!")
            return 0

        # Extract text and metadata
        print(f"Processing {len(raw_logs)} log entries...")
        records = self.extractor.to_records(raw_logs)
        if not records:
            print("No valid text extracted!")
            return 0

        # Generate embeddings
        print(f"Creating embeddings for {len(records)} records...")
        texts = [r.text for r in records]
        embeddings = self.embedder.encode(texts)

        # Store in database
        print("Storing in ChromaDB...")
        self.store.add(records, embeddings)

        print(
            f"✅ Stored {len(records)} logs in '{self.cfg.collection_name}' collection"
        )
        return len(records)

    def search_logs(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search stored logs for similar content."""
        print(f"Searching for: '{query}'")
        query_embedding = self.embedder.encode([query])[0]
        return self.store.search(query_embedding, n_results)
