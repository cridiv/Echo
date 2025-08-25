from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import numpy as np
import uuid


class SourceType(Enum):
    PATTERN_AGENT = "pattern"
    SEMANTIC_AGENT = "semantic"
    LOG_AGENT = "log"
    ORACLE_FEEDBACK = "oracle"
    HUMAN_REVIEW = "human"
    CROSS_INCIDENT = "cross"


class QualityFlag(Enum):
    PARSING_QUALITY = "parsing"
    SOURCE_RELIABILITY = "source"
    SEMANTIC_COHERENCE = "semantic"
    TEMPORAL_RELEVANCE = "temporal"


@dataclass
class LabeledExperience:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_data: Dict[str, Any] = field(default_factory=dict)
    labels: List[Tuple[str, float]] = field(default_factory=list)
    quality_flags: Dict[str, float] = field(default_factory=dict)
    embedding_vector: Optional[np.ndarray] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_type: SourceType = SourceType.LOG_AGENT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_primary_label(self) -> Optional[Tuple[str, float]]:
        if not self.labels:
            return None
        return max(self.labels, key=lambda x: x[1])

    def is_ready_for_learning(
        self, min_confidence: float = 0.7, min_quality: float = 0.5
    ) -> bool:
        has_confident_label = any(conf >= min_confidence for _, conf in self.labels)
        avg_quality = (
            sum(self.quality_flags.values()) / len(self.quality_flags)
            if self.quality_flags
            else 0.0
        )
        return (
            has_confident_label
            and avg_quality >= min_quality
            and self.embedding_vector is not None
        )


@dataclass
class ExperienceBatch:
    experiences: List[LabeledExperience] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 1

    def add_experience(self, experience: LabeledExperience) -> None:
        self.experiences.append(experience)

    def get_ready_for_learning(self, experience: LabeledExperience) -> bool:
        return [exp for exp in self.experiences if exp.is_ready_for_learning()]


# Thresholds
CONFIDENCE_THRESHOLDS = {"high": 0.8, "medium": 0.6, "low": 0.4, "reject": 0.2}

QUALITY_THRESHOLDS = {"good": 0.7, "acceptable": 0.5, "poor": 0.3}
