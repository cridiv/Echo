import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from Semantic.embeddings import SemanticAgent
from bayesian_updater import BayesianConfidenceUpdater, AgentResult
from taxonomy import LabelTaxonomyManager, LabelCandidate, LabelRecord
from label_graph import LabelGraph
from Semantic.embeddings import SentenceEmbedder


class SemanticCoordinationAgent:
    """Coordinates semantic analysis, agent confidence tracking, and label taxonomy management."""

    def __init__(
        self,
        eps: float = 0.15,
        min_samples: int = 5,
        promotion_min_size: int = 10,
        promotion_min_confidence: float = 0.65,
        review_max_label_entropy: float = 0.8,
        similarity_threshold: float = 0.6,
    ):

        # Initialize core components
        self.semantic_agent = SemanticAgent()
        self.confidence_updater = BayesianConfidenceUpdater()

        # Initialize taxonomy manager
        self.taxonomy_manager = LabelTaxonomyManager(
            semantic_agent=self.semantic_agent,
            eps=eps,
            min_samples=min_samples,
            promotion_min_size=promotion_min_size,
            promotion_min_confidence=promotion_min_confidence,
            review_max_label_entropy=review_max_label_entropy,
        )

        # Initialize label relationship graph
        self.label_graph = LabelGraph(similarity_threshold=similarity_threshold)

    def process_logs_with_confidence(
        self,
        logs: List[str],
        agent_confidences: Dict[int, float],
        suggested_labels: Optional[Dict[int, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Process logs through the full semantic pipeline."""

        # Discover clusters using taxonomy manager
        candidates = self.taxonomy_manager.discover_clusters(
            logs, agent_confidences, suggested_labels
        )

        # Evaluate and promote candidates
        promoted, queued = self.taxonomy_manager.evaluate_and_promote(candidates)

        # Update label graph with new promoted labels
        for label_record in promoted:
            self.label_graph.add_label(label_record.name, label_record.centroid)

        # Rebuild relationships if we have new labels
        if promoted:
            self.label_graph.build_relationships()

        return {
            "discovered_candidates": len(candidates),
            "promoted_labels": len(promoted),
            "queued_for_review": len(queued),
            "promoted_label_ids": [lr.id for lr in promoted],
            "review_queue_ids": [lc.id for lc in queued],
        }

    def record_agent_result(self, agent_id: str, output: Any, success: bool) -> None:
        """Record agent performance for confidence tracking."""
        self.agent_coordinator.receive_result(agent_id, output, success)

    def get_agent_confidences(self) -> Dict[str, float]:
        """Get confidence scores for all tracked agents."""
        return self.agent_coordinator.get_all_confidences()

    def find_similar_labels(
        self, query_text: str, top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """Find labels most similar to a query text."""
        return self.taxonomy_manager.find_closest_label(query_text, top_k)

    def get_related_labels(self, label: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Get labels related to a given label through the knowledge graph."""
        return self.label_graph.get_related_labels(label, top_k)

    def approve_review_item(
        self, candidate_id: str, label_name: Optional[str] = None
    ) -> Optional[LabelRecord]:
        """Approve a candidate from the review queue."""
        approved_record = self.taxonomy_manager.approve_review_item(
            candidate_id, label_name
        )

        # Add to label graph if approved
        if approved_record:
            self.label_graph.add_label(approved_record.name, approved_record.centroid)
            self.label_graph.build_relationships()

        return approved_record

    def get_review_queue(self) -> Dict[str, LabelCandidate]:
        """Get current items in review queue."""
        return self.taxonomy_manager.inspect_review_queue()

    def get_taxonomy_summary(self) -> Dict[str, Any]:
        """Get summary of current taxonomy state."""
        return {
            "total_labels": len(self.taxonomy_manager.taxonomy),
            "review_queue_size": len(self.taxonomy_manager.review_queue),
            "label_graph_nodes": self.label_graph.graph.number_of_nodes(),
            "label_graph_edges": self.label_graph.graph.number_of_edges(),
        }

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        return self.semantic_agent.embed(texts)

    def update_label_relationship(
        self, label_a: str, label_b: str, adjustment: float = 0.05
    ):
        """Dynamically adjust relationship strength between labels."""
        self.label_graph.update_relationship(label_a, label_b, adjustment)


# Main interface functions for external use
def create_semantic_coordination_agent(**kwargs) -> SemanticCoordinationAgent:
    """Factory function to create a new semantic coordination agent."""
    return SemanticCoordinationAgent(**kwargs)


def process_semantic_logs(
    agent: SemanticCoordinationAgent,
    logs: List[str],
    confidences: Dict[int, float],
    labels: Optional[Dict[int, List[str]]] = None,
) -> Dict[str, Any]:
    """Process logs through semantic analysis pipeline."""
    return agent.process_logs_with_confidence(logs, confidences, labels)


def track_agent_performance(
    agent: SemanticCoordinationAgent, agent_id: str, output: Any, success: bool
) -> None:
    """Track an agent's performance."""
    agent.record_agent_result(agent_id, output, success)


def find_similar_labels(
    agent: SemanticCoordinationAgent, query: str, top_k: int = 3
) -> List[Tuple[str, float]]:
    """Find labels similar to query text."""
    return agent.find_similar_labels(query, top_k)


def approve_label_candidate(
    agent: SemanticCoordinationAgent,
    candidate_id: str,
    label_name: Optional[str] = None,
) -> Optional[LabelRecord]:
    """Approve a label candidate from review queue."""
    return agent.approve_review_item(candidate_id, label_name)
