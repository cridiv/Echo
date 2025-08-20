from collections import defaultdict
from typing import Dict
from Semantic.embeddings import LogExtractor


class ErrorFrequencyTracker:
    def __init__(self):
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.extractor = LogExtractor()

    def record(self, category: str) -> None:
        text, metadata = self.extractor._extract_text_and_metadata(category)

        category = text if text else "Unknown"

        self.error_counts[category] += 1

    def get_frequency(self, category: str) -> int:
        return self.error_counts.get(category, 0)

    def all_frequencies(self) -> Dict[str, int]:
        return dict(self.error_counts)
