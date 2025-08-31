import random
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AgentResult:
    agent_id: str
    success: bool
    output: Any


class BayesianConfidenceUpdater:
    def __init__(self):
        self.agent_params: Dict[str, Dict[str, float]] = {}

    def initialize_agent(self, agent_id: str):
        if agent_id not in self.agent_params:
            self.agent_params[agent_id] = {"alpha": 1.0, "beta": 1.0}

    def update_confidence(self, agent_id: str, outcome: bool):
        self.initialize_agent(agent_id)
        params = self.agent_params[agent_id]

        if outcome:
            params["alpha"] += 1
        else:
            params["beta"] += 1

    def get_confidence(self, agent_id: str) -> float:
        params = self.agent_params.get(agent_id, {"alpha": 1.0, "beta": 1.0})
        return params["alpha"] / (params["alpha"] + params["beta"])


class AgentCoordinator:
    def __init__(self, updater: BayesianConfidenceUpdater):
        self.updater = updater
        self.results: Dict[str, AgentResult] = {}

    def receive_result(self, agent_id: str, output: Any, success: bool):

        self.results[agent_id] = AgentResult(agent_id, output, success)

        self.updater.update_confidence(agent_id, success)

    def get_agent_confidence(self, agent_id: str) -> float:
        return self.updater.get_confidence(agent_id)

    def get_all_confidences(self) -> Dict[str, float]:
        return {
            agent_id: self.get_agent_confidence(agent_id)
            for agent_id in self.results.keys()
        }
