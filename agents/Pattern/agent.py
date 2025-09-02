from typing import Dict, Any, List, Tuple, Optional
from .embeddings import PatternStore
from .pattern_recognition import ErrorFrequencyTracker
from .resolution_tracker import ResolutionTracker
from Semantic.embeddings import LogExtractor


class PatternAnalysisAgent:
    """Coordinates pattern analysis, error tracking, and resolution management."""

    def __init__(self):
        self.pattern_store = PatternStore()
        self.error_tracker = ErrorFrequencyTracker()
        self.resolution_tracker = ResolutionTracker()
        self.log_extractor = LogExtractor()

    def process_log_entry(self, log_data: Any, metadata: Dict[str, Any] = None) -> str:
        """Process a single log entry through all tracking systems."""
        if metadata is None:
            metadata = {}

        # Extract text and metadata
        text, extracted_metadata = self.log_extractor._extract_text_and_metadata(
            log_data
        )

        # Merge metadata
        combined_metadata = {**extracted_metadata, **metadata}

        # Add to pattern store
        pattern_id = self.pattern_store.add_log(text, combined_metadata)

        # Record error frequency
        self.error_tracker.record(text)

        return pattern_id

    def add_solution_to_pattern(self, pattern_id: str, solution: str) -> None:
        """Add a solution to a specific pattern."""
        self.pattern_store.add_solution(pattern_id, solution)

    def record_resolution_effectiveness(
        self, error_category: str, resolution: str, was_effective: bool
    ) -> None:
        """Record how effective a resolution was for an error category."""
        self.resolution_tracker.record(error_category, resolution, was_effective)

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis of patterns, errors, and resolutions."""
        return {
            "trending_patterns": self.pattern_store.get_trending_patterns(),
            "top_errors": self.error_tracker.top_errors(),
            "total_patterns": len(self.pattern_store.patterns),
            "total_error_categories": len(self.error_tracker.error_counts),
        }

    def get_recommended_solution(self, error_category: str) -> Optional[str]:
        """Get the best recommended solution for an error category."""
        return self.resolution_tracker.best_resolution(error_category)

    def process_batch_logs(self, logs: List[Any]) -> List[str]:
        """Process multiple log entries and return their pattern IDs."""
        pattern_ids = []
        for log_data in logs:
            pattern_id = self.process_log_entry(log_data)
            pattern_ids.append(pattern_id)
        return pattern_ids


# Main interface functions for external use
def create_pattern_analysis_agent() -> PatternAnalysisAgent:
    """Factory function to create a new pattern analysis agent."""
    return PatternAnalysisAgent()


def analyze_logs(agent: PatternAnalysisAgent, logs: List[Any]) -> Dict[str, Any]:
    """Analyze a batch of logs and return summary."""
    pattern_ids = agent.process_batch_logs(logs)
    summary = agent.get_analysis_summary()
    summary["processed_pattern_ids"] = pattern_ids
    return summary


def add_solution(agent: PatternAnalysisAgent, pattern_id: str, solution: str) -> None:
    """Add a solution to a pattern."""
    agent.add_solution_to_pattern(pattern_id, solution)


def track_resolution(
    agent: PatternAnalysisAgent, error_category: str, resolution: str, effective: bool
) -> None:
    """Track the effectiveness of a resolution."""
    agent.record_resolution_effectiveness(error_category, resolution, effective)
