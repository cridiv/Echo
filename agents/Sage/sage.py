from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import OpenAI
from dataclasses import dataclass
import json
from Log.ingest import LogAgent
from Semantic.agent import SemanticAgent
from Pattern.agent import PatternAnalysisAgent
from Oracle.oracle_agent import OracleAgent


@dataclass
class AgentOutput:
    """Structured container for agent outputs."""

    agent_name: str
    data: Any
    confidence: float
    timestamp: str
    success: bool
    error_message: Optional[str] = None


class SageOrchestrator:
    """
    Master orchestrator that coordinates all specialized agents and performs
    context engineering to provide unified insights.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()

        # Initialize specialized agents
        self.log_agent = None  # Will call LogAgent() function when needed
        self.semantic_agent = SemanticAgent()
        self.pattern_agent = PatternAnalysisAgent()
        self.oracle_agent = OracleAgent()

        # Track agent reliability over time
        self.agent_reliability = {
            "log_agent": 0.8,
            "semantic_agent": 0.75,
            "pattern_agent": 0.7,
            "oracle_agent": 0.85,
        }

    def orchestrate_analysis(
        self, query: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration method that coordinates all agents and provides unified insight.

        Args:
            query: The analysis query or problem statement
            context: Optional additional context for the analysis

        Returns:
            Unified analysis result with final recommendations
        """
        if context is None:
            context = {}

        timestamp = datetime.now().isoformat()

        # Step 1: Gather data from all agents
        agent_outputs = self._gather_agent_outputs(query, context)

        # Step 2: Perform context engineering
        unified_context = self._engineer_context(agent_outputs, query)

        # Step 3: Generate final insight using GPT
        final_insight = self._generate_final_insight(unified_context, query)

        # Step 4: Update agent reliability based on consistency
        self._update_reliability_scores(agent_outputs)

        return {
            "timestamp": timestamp,
            "query": query,
            "agent_outputs": {
                output.agent_name: output.data for output in agent_outputs
            },
            "unified_context": unified_context,
            "final_insight": final_insight,
            "confidence_score": self._calculate_overall_confidence(agent_outputs),
            "contributing_agents": [
                output.agent_name for output in agent_outputs if output.success
            ],
        }

    def _gather_agent_outputs(
        self, query: str, context: Dict[str, Any]
    ) -> List[AgentOutput]:
        """Collect outputs from all specialized agents."""
        outputs = []

        # 1. Log Agent - Get and process logs
        try:
            logs = LogAgent()  # This returns parsed logs
            log_output = AgentOutput(
                agent_name="log_agent",
                data={"parsed_logs": logs, "count": len(logs) if logs else 0},
                confidence=0.9 if logs else 0.1,
                timestamp=datetime.now().isoformat(),
                success=bool(logs),
            )
            outputs.append(log_output)
        except Exception as e:
            outputs.append(
                AgentOutput(
                    agent_name="log_agent",
                    data={},
                    confidence=0.0,
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message=str(e),
                )
            )

        # 2. Semantic Agent - Analyze semantic patterns
        if outputs and outputs[-1].success:
            try:
                logs = outputs[-1].data["parsed_logs"]
                log_texts = [str(log) for log in logs[:100]]  # Limit for efficiency

                semantic_result = self.semantic_agent.process_logs_with_confidence(
                    logs=log_texts,
                    agent_confidences={i: 0.8 for i in range(len(log_texts))},
                )

                semantic_output = AgentOutput(
                    agent_name="semantic_agent",
                    data=semantic_result,
                    confidence=min(0.9, semantic_result.get("promoted_labels", 0) / 10),
                    timestamp=datetime.now().isoformat(),
                    success=True,
                )
                outputs.append(semantic_output)
            except Exception as e:
                outputs.append(
                    AgentOutput(
                        agent_name="semantic_agent",
                        data={},
                        confidence=0.0,
                        timestamp=datetime.now().isoformat(),
                        success=False,
                        error_message=str(e),
                    )
                )

        # 3. Pattern Agent - Identify patterns and trends
        if outputs and outputs[0].success:
            try:
                logs = outputs[0].data["parsed_logs"]
                pattern_result = self.pattern_agent.process_batch_logs(logs)
                analysis_summary = self.pattern_agent.get_analysis_summary()

                pattern_output = AgentOutput(
                    agent_name="pattern_agent",
                    data={
                        "pattern_ids": pattern_result,
                        "analysis_summary": analysis_summary,
                    },
                    confidence=min(0.8, len(pattern_result) / 50),
                    timestamp=datetime.now().isoformat(),
                    success=True,
                )
                outputs.append(pattern_output)
            except Exception as e:
                outputs.append(
                    AgentOutput(
                        agent_name="pattern_agent",
                        data={},
                        confidence=0.0,
                        timestamp=datetime.now().isoformat(),
                        success=False,
                        error_message=str(e),
                    )
                )

        # 4. Oracle Agent - Generate insights and recommendations
        semantic_data = []
        pattern_data = []

        for output in outputs:
            if output.agent_name == "semantic_agent" and output.success:
                semantic_data = [output.data]
            elif output.agent_name == "pattern_agent" and output.success:
                pattern_data = [output.data]

        try:
            oracle_result = self.oracle_agent.analyze(semantic_data, pattern_data)
            oracle_output = AgentOutput(
                agent_name="oracle_agent",
                data=oracle_result,
                confidence=oracle_result.get("confidence_score", 0.5),
                timestamp=datetime.now().isoformat(),
                success=True,
            )
            outputs.append(oracle_output)
        except Exception as e:
            outputs.append(
                AgentOutput(
                    agent_name="oracle_agent",
                    data={},
                    confidence=0.0,
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message=str(e),
                )
            )

        return outputs

    def _engineer_context(
        self, agent_outputs: List[AgentOutput], query: str
    ) -> Dict[str, Any]:
        """Merge and filter agent outputs into unified context."""
        context = {
            "query": query,
            "successful_agents": [],
            "failed_agents": [],
            "key_findings": {},
            "confidence_weights": {},
        }

        for output in agent_outputs:
            if output.success:
                context["successful_agents"].append(output.agent_name)
                context["key_findings"][output.agent_name] = output.data
                context["confidence_weights"][output.agent_name] = (
                    output.confidence
                    * self.agent_reliability.get(output.agent_name, 0.5)
                )
            else:
                context["failed_agents"].append(
                    {"agent": output.agent_name, "error": output.error_message}
                )

        return context

    def _generate_final_insight(
        self, unified_context: Dict[str, Any], query: str
    ) -> str:
        """Use GPT to generate final insight from unified context."""

        # Prepare context for GPT
        context_summary = self._prepare_context_for_gpt(unified_context)

        prompt = f"""
You are Sage, a master orchestrator analyzing system logs and patterns. Based ONLY on the information provided by specialized agents, provide a comprehensive analysis and recommendations.

QUERY: {query}

AGENT FINDINGS:
{context_summary}

INSTRUCTIONS:
1. Synthesize findings from all successful agents
2. Identify the most critical issues based on agent confidence and evidence
3. Provide actionable recommendations
4. Highlight any conflicting information between agents
5. Base conclusions ONLY on the provided agent data

Provide a clear, structured response with:
- Summary of key findings
- Priority issues identified
- Recommended actions
- Confidence assessment
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Sage, a master orchestrator that provides insights based solely on agent findings. Never add information not provided by the agents.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error generating final insight: {str(e)}. Please review individual agent outputs."

    def _prepare_context_for_gpt(self, unified_context: Dict[str, Any]) -> str:
        """Convert unified context to readable format for GPT."""
        context_parts = []

        for agent_name, findings in unified_context["key_findings"].items():
            confidence = unified_context["confidence_weights"].get(agent_name, 0.0)
            context_parts.append(
                f"\n{agent_name.upper()} (Confidence: {confidence:.2f}):"
            )

            if isinstance(findings, dict):
                context_parts.append(json.dumps(findings, indent=2))
            else:
                context_parts.append(str(findings))

        if unified_context["failed_agents"]:
            context_parts.append(f"\nFAILED AGENTS: {unified_context['failed_agents']}")

        return "\n".join(context_parts)

    def _calculate_overall_confidence(self, agent_outputs: List[AgentOutput]) -> float:
        """Calculate overall confidence based on agent outputs and reliability."""
        if not agent_outputs:
            return 0.0

        total_weighted_confidence = 0.0
        total_weight = 0.0

        for output in agent_outputs:
            if output.success:
                reliability = self.agent_reliability.get(output.agent_name, 0.5)
                weight = output.confidence * reliability
                total_weighted_confidence += weight
                total_weight += reliability

        return round(
            total_weighted_confidence / total_weight if total_weight > 0 else 0.0, 3
        )

    def _update_reliability_scores(self, agent_outputs: List[AgentOutput]) -> None:
        """Update agent reliability based on consistency and success rates."""
        # Simple reliability update - can be enhanced with more sophisticated logic
        for output in agent_outputs:
            current_reliability = self.agent_reliability.get(output.agent_name, 0.5)

            if output.success:
                # Slight increase for successful execution
                self.agent_reliability[output.agent_name] = min(
                    0.95, current_reliability + 0.01
                )
            else:
                # Slight decrease for failures
                self.agent_reliability[output.agent_name] = max(
                    0.1, current_reliability - 0.02
                )


# Factory function for easy instantiation
def create_sage_orchestrator(openai_api_key: Optional[str] = None) -> SageOrchestrator:
    """Create a new Sage orchestrator instance."""
    return SageOrchestrator(openai_api_key)


# Main interface function
def orchestrate_log_analysis(
    query: str, context: Dict[str, Any] = None, openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level function to orchestrate complete log analysis.

    Args:
        query: Analysis query or problem statement
        context: Optional additional context
        openai_api_key: OpenAI API key (optional if set as environment variable)

    Returns:
        Comprehensive analysis result
    """
    sage = create_sage_orchestrator(openai_api_key)
    return sage.orchestrate_analysis(query, context)
