import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer, util
from typing import Dict, Any, List, Tuple


@dataclass
class PatternStore:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    patterns: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    similarity_threshold: float = 0.75

    def add_log(self, log_text: str, metadata: Dict[str, Any]) -> str:

        new_embedding = self.model.encode(log_text, convert_to_tensor=True)

        for pattern_id, pattern_data in self.patterns.items():
            existing_embedding = pattern_data["embedding"]

            similarity = util.cos_sim(new_embedding, existing_embedding).item()

            if similarity >= self.similarity_threshold:
                self.patterns[pattern_id]["frequency"] += 1
                self.patterns[pattern_id]["history"].append(
                    {
                        "text": log_text,
                        "metadata": metadata,
                    }
                )

                return pattern_id

        new_id = str(uuid.uuid4())
        self.patterns[new_id] = {
            "embedding": new_embedding,
            "representative_text": log_text,
            "frequency": 1,
            "history": [
                {
                    "text": log_text,
                    "metadata": metadata,
                }
            ],
            "solutions": [],
        }

        return new_id

    def add_solution(self, pattern_id: str, solution_text: str) -> None:
        if pattern_id not in self.patterns:
            raise ValueError(f"Pattern ID {pattern_id} does not exist.")

        self.patterns[pattern_id]["solutions"].append(solution_text)

    def get_trending_patterns(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        Return top N frequent error patterns.
        Output: List of (pattern_id, frequency)
        """
        sorted_patterns = sorted(
            self.patterns.items(), key=lambda x: x[1]["frequency"], reverse=True
        )
        return [(pid, pdata["frequency"]) for pid, pdata in sorted_patterns[:top_n]]
