from typing import List, Dict, Any, Optional, Tuple
from .embeddings import LogEmbeddingPipeline, EmbeddingConfig


class SemanticAgent:
    """
    Coordinates between log embedding pipeline and (later) taxonomy manager.
    Handles:
    - Ingestion & semantic storage
    - Search & retrieval
    - Future: taxonomy clustering, confidence scoring, review workflows
    """

    def __init__(self, cfg: Optional[EmbeddingConfig] = None):
        self.pipeline = LogEmbeddingPipeline(cfg or EmbeddingConfig())
        # self.taxonomy_mgr = LabelTaxonomyManager()   # not yet wired

    # -------------------- Ingestion --------------------
    def process_and_store(self, logs: List[Any]) -> int:
        """
        Run embedding pipeline on new logs and store them in vector DB.
        """
        print(f"🌀 Coordinator: processing {len(logs)} logs...")
        records = self.pipeline.extractor.to_records(logs)
        if not records:
            print("No valid records to store.")
            return 0

        embeddings = self.pipeline.embedder.encode([r.text for r in records])
        self.pipeline.store.add(records, embeddings)
        print(f"✅ Stored {len(records)} logs via coordinator.")
        return len(records)

    # -------------------- Search --------------------
    def semantic_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Perform semantic similarity search over stored logs.
        """
        print(f"🔍 Coordinator searching for: '{query}'")
        return self.pipeline.search_logs(query, n_results)

    def match_to_labels(self, log: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        (Stub) Match log to existing taxonomy labels.
        Later will integrate with LabelTaxonomyManager.
        """
        print(f"(TODO) Matching log to taxonomy labels: {log}")
        return []
