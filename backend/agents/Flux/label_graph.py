import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity


class LabelGraph:
    """
    Builds a knowledge graph of cross-label relationships.
    Nodes = labels
    Edges = similarity-based relationships
    """

    def __init__(self, similarity_threshold: float = 0.6):
        """
        :param similarity_threshold: minimum cosine similarity
                                     to create an edge between labels
        """
        self.graph = nx.Graph()
        self.similarity_threshold = similarity_threshold
        self.label_embeddings: Dict[str, np.ndarray] = {}

    def add_label(self, label: str, embedding: np.ndarray):
        """
        Add a label + its embedding to the graph
        """
        self.label_embeddings[label] = embedding
        self.graph.add_node(label)

    def build_relationships(self):
        """
        Compare all labels pairwise and create weighted edges
        """
        labels = list(self.label_embeddings.keys())
        embeddings = np.array([self.label_embeddings[l] for l in labels])

        # Compute cosine similarity matrix
        sim_matrix = cosine_similarity(embeddings)

        # Iterate over pairs
        for i, label_a in enumerate(labels):
            for j, label_b in enumerate(labels):
                if i >= j:  # avoid duplicates & self-loops
                    continue

                sim = sim_matrix[i][j]
                if sim >= self.similarity_threshold:
                    self.graph.add_edge(label_a, label_b, weight=sim)

    def update_relationship(self, label_a: str, label_b: str, adjustment: float = 0.05):
        """
        Adjust relationship strength dynamically (e.g., when system notices co-occurrence).
        """
        if self.graph.has_edge(label_a, label_b):
            self.graph[label_a][label_b]["weight"] += adjustment
            # Cap the weight at 1.0
            self.graph[label_a][label_b]["weight"] = min(
                1.0, self.graph[label_a][label_b]["weight"]
            )

    def get_related_labels(self, label: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Retrieve most strongly related labels
        """
        if label not in self.graph:
            return []

        neighbors = self.graph[label]
        sorted_neighbors = sorted(
            neighbors.items(), key=lambda x: x[1]["weight"], reverse=True
        )
        return [(n, data["weight"]) for n, data in sorted_neighbors[:top_k]]

    def visualize(self):
        """
        (Optional) Quick visualization using matplotlib
        """
        import matplotlib.pyplot as plt

        pos = nx.spring_layout(self.graph, seed=42)
        weights = nx.get_edge_attributes(self.graph, "weight")

        nx.draw(
            self.graph,
            pos,
            with_labels=True,
            node_size=1500,
            node_color="skyblue",
            font_size=10,
        )
        nx.draw_networkx_edge_labels(
            self.graph, pos, edge_labels={k: f"{v:.2f}" for k, v in weights.items()}
        )
        plt.show()
