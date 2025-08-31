from typing import Dict, Optional


class ResolutionTracker:
    """Tracks solutions applied to errors and how effective they are."""

    def __init__(self):
        self.resolutions: Dict[str, Dict[str, Dict[str, int]]] = {}

    def record(self, category: str, resolution: str, effective: bool) -> None:
        """Store resolution usage and effectiveness for an error category."""
        if category not in self.resolutions:
            self.resolutions[category] = {}

        if resolution not in self.resolutions[category]:
            self.resolutions[category][resolution] = {"count": 0, "effective": 0}

        self.resolutions[category][resolution]["count"] += 1
        if effective:
            self.resolutions[category][resolution]["effective"] += 1

    def best_resolution(self, category: str) -> Optional[str]:
        """Return the resolution with the highest effectiveness ratio."""
        if category not in self.resolutions or not self.resolutions[category]:
            return None

        resolutions = self.resolutions[category]

        # Find resolution with best effectiveness rate
        best = max(
            resolutions.items(),
            key=lambda r: (
                r[1]["effective"] / r[1]["count"] if r[1]["count"] > 0 else 0,
                r[1]["count"],  # tie-breaker: prefer more frequently used
            ),
        )

        return best[0]  # resolution name
