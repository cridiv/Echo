import uuid
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
from Semantic.embeddings import SentenceEmbedder


# -------------------- Semantic Agent --------------------
class SemanticAgent:
    def embed(self, texts: List[str]) -> np.ndarray:
        return SentenceEmbedder.encode(texts)


# -------------------- Data Classes --------------------
@dataclass
class LabelCandidate:
    id: str
    member_indices: List[int]
    centroid: np.ndarray
    size: int
    mean_confidence: float
    label_suggestions: Dict[str, int] = field(default_factory=dict)


@dataclass
class LabelRecord:
    id: str
    name: str
    centroid: np.ndarray
    members: List[int]
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# -------------------- Taxonomy Manager --------------------
class LabelTaxonomyManager:
    def __init__(
        self,
        semantic_agent: SemanticAgent,
        eps: float = 0.15,
        min_samples: int = 5,
        promotion_min_size: int = 10,
        promotion_min_confidence: float = 0.65,
        review_max_label_entropy: float = 0.8,
    ):
        """
        :param semantic_agent: the semantic agent used for embeddings
        :param eps: DBSCAN eps parameter (distance threshold). Use cosine distance.
        :param min_samples: DBSCAN min samples for a core point.
        :param promotion_min_size: minimum cluster size to consider auto-promotion.
        :param promotion_min_confidence: minimum mean agent confidence for auto-promotion.
        :param review_max_label_entropy: clusters with high label suggestion entropy go for review.
        """
        self.semantic_agent = semantic_agent
        self.eps = eps
        self.min_samples = min_samples
        self.promotion_min_size = promotion_min_size
        self.promotion_min_confidence = promotion_min_confidence
        self.review_max_label_entropy = review_max_label_entropy

        # persistent taxonomy (label_id -> LabelRecord)
        self.taxonomy: Dict[str, LabelRecord] = {}

        # review queue holds LabelCandidates for human inspection
        self.review_queue: Dict[str, LabelCandidate] = {}

    # -------------------- Core pipeline --------------------
    def discover_clusters(
        self,
        logs: List[str],
        agent_confidences: Dict[int, float],
        suggested_labels: Optional[Dict[int, List[str]]] = None,
    ) -> List[LabelCandidate]:
        """
        Discover clusters from raw logs. Embeddings are computed automatically.
        :param logs: list of raw log strings
        :param agent_confidences: mapping from log index -> confidence score (0..1)
        :param suggested_labels: optional mapping from log index -> list of label strings suggested by agents
        :return: list of LabelCandidate
        """
        if len(logs) == 0:
            return []

        # 🔑 Embed logs automatically
        embeddings = self.semantic_agent.embed(logs)

        # compute cosine distance matrix
        dist = cosine_distances(embeddings)

        # run DBSCAN on distance matrix
        db = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="precomputed")
        cluster_ids = db.fit_predict(dist)

        candidates: Dict[int, List[int]] = {}
        for idx, cid in enumerate(cluster_ids):
            if cid == -1:
                continue  # noise
            candidates.setdefault(cid, []).append(idx)

        label_candidates: List[LabelCandidate] = []
        for cid, members in candidates.items():
            member_embeddings = embeddings[members]
            centroid = np.mean(member_embeddings, axis=0)
            size = len(members)

            # compute mean confidence
            confidences = [agent_confidences.get(i, 0.5) for i in members]
            mean_conf = float(np.mean(confidences)) if confidences else 0.5

            # collect suggested labels
            label_suggestions: Dict[str, int] = {}
            if suggested_labels:
                for i in members:
                    for lbl in suggested_labels.get(i, []):
                        label_suggestions[lbl] = label_suggestions.get(lbl, 0) + 1

            candidate = LabelCandidate(
                id=str(uuid.uuid4()),
                member_indices=members,
                centroid=centroid,
                size=size,
                mean_confidence=mean_conf,
                label_suggestions=label_suggestions,
            )
            label_candidates.append(candidate)

        return label_candidates

    # -------------------- Promotion / Review --------------------
    def _label_entropy(self, suggestions: Dict[str, int]) -> float:
        if not suggestions:
            return 0.0
        total = sum(suggestions.values())
        probs = [v / total for v in suggestions.values()]
        entropy = -sum(p * np.log(p + 1e-12) for p in probs)
        max_ent = np.log(len(probs)) if len(probs) > 1 else 1.0
        return float(entropy / (max_ent + 1e-12))

    def evaluate_and_promote(
        self, candidates: List[LabelCandidate]
    ) -> Tuple[List[LabelRecord], List[LabelCandidate]]:
        promoted: List[LabelRecord] = []
        queued: List[LabelCandidate] = []

        for cand in candidates:
            if (
                cand.size >= self.promotion_min_size
                and cand.mean_confidence >= self.promotion_min_confidence
            ):
                entropy = self._label_entropy(cand.label_suggestions)
                if entropy <= self.review_max_label_entropy:
                    label_name = self._synthesize_label_name(cand)
                    rec = LabelRecord(
                        id=cand.id,
                        name=label_name,
                        centroid=cand.centroid,
                        members=cand.member_indices.copy(),
                        created_at=self._now_ts(),
                        metadata={
                            "mean_confidence": cand.mean_confidence,
                            "size": cand.size,
                            "label_suggestions": cand.label_suggestions,
                        },
                    )
                    self.taxonomy[rec.id] = rec
                    promoted.append(rec)
                    continue
            self.review_queue[cand.id] = cand
            queued.append(cand)

        return promoted, queued

    def _synthesize_label_name(self, candidate: LabelCandidate) -> str:
        if candidate.label_suggestions:
            best = max(candidate.label_suggestions.items(), key=lambda x: x[1])[0]
            return best
        return f"label_{candidate.id[:8]}"

    def _now_ts(self) -> float:
        return float(np.datetime64("now").astype("datetime64[s]").astype(int))

    # -------------------- Utilities --------------------
    def find_closest_label(self, log: str, top_k: int = 1) -> List[Tuple[str, float]]:
        """Embed log and return top-k closest existing labels"""
        if not self.taxonomy:
            return []
        embedding = self.semantic_agent.embed([log])[0]
        labels = list(self.taxonomy.values())
        centroids = np.stack([l.centroid for l in labels])
        dists = cosine_distances(centroids, embedding.reshape(1, -1)).squeeze()
        idxs = np.argsort(dists)[:top_k]
        return [(labels[i].id, float(dists[i])) for i in idxs]

    def inspect_review_queue(self) -> Dict[str, LabelCandidate]:
        return self.review_queue

    def approve_review_item(
        self, candidate_id: str, label_name: Optional[str] = None
    ) -> Optional[LabelRecord]:
        cand = self.review_queue.pop(candidate_id, None)
        if not cand:
            return None
        name = label_name or self._synthesize_label_name(cand)
        rec = LabelRecord(
            id=cand.id,
            name=name,
            centroid=cand.centroid,
            members=cand.member_indices.copy(),
            created_at=self._now_ts(),
            metadata={
                "mean_confidence": cand.mean_confidence,
                "size": cand.size,
                "label_suggestions": cand.label_suggestions,
            },
        )
        self.taxonomy[rec.id] = rec
        return rec
