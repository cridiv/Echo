from typing import List, Dict, Any
from datetime import datetime
from openai import OpenAI


client = OpenAI()


class OracleAgent:
    def __init__(self):
        self.confidence_threshold = 0.7
        self.max_suggestions = 5

    def analyze(
        self, semantic_results: List[Dict], pattern_results: List[Dict]
    ) -> Dict[str, any]:
        analysis_report = {
            "timestamp": datetime.now().isoformat(),
            "probable_causes": [],
            "confidence_score": 0.0,
            "recommendations": [],
            "analysis_summary": "",
        }

        combined_insights = self._combine_data_sources(
            semantic_results, pattern_results
        )

        probable_cause = self._identify_probable_cause(combined_insights)

        recommendations = self._generate_recommendations(
            probable_cause, combined_insights
        )

        confidence_score = self._calculate_confidence(probable_cause, recommendations)

        summary = self._create_analysis_summary(
            probable_cause, confidence_score, recommendations
        )

        analysis_report.update(
            {
                "probable_causes": probable_cause,
                "confidence_score": confidence_score,
                "recommendations": recommendations,
                "analysis_summary": summary,
            }
        )

        return analysis_report

    def _combine_data_sources(
        self, semantic_results: List[Dict], pattern_results: List[Dict]
    ) -> Dict:
        combined = {
            "semantic_results": semantic_results,
            "pattern_results": pattern_results,
        }

        for result in semantic_results + pattern_results:
            combined.setdefault("all_results", []).append(result)
        return combined

    def _identify_probable_cause(self, combined_insights: Dict) -> List[Dict]:
        probable_causes = []

        for semantic_results in combined_insights["semantic_results"]:
            cause = {
                "cause": f"issue indicated by {semantic_results.get("category", "unknown")}",
                "source": "semantic_results",
                "confidence_score": semantic_results.get("score", 0.5),
            }

            probable_causes.append(cause)

        for pattern_result in combined_insights["pattern_insights"]:
            cause = {
                "cause": f"Recurring pattern: {pattern_result.get('pattern_type', 'Unknown pattern')}",
                "source": "pattern_analysis",
                "confidence": pattern_result.get("match_confidence", 0.5),
                "historical_resolution": pattern_result.get(
                    "past_resolution", "No resolution recorded"
                ),
            }
            probable_causes.append(cause)

        analyzed_causes = []
        for cause in probable_causes:
            prompt = f"""
            You are an expert system analyzing error causes.
            Here is a detected cause:
            {cause}

            Please:
            1. Refine this cause into plain language.
            2. Suggest a possible resolution based on experience.
            3. Provide a confidence estimate (0-1).
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are OracleAgent, an expert in diagnosing system logs.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            refined = response.choices[0].message.content.strip()

            cause["llm_analysis"] = refined
            analyzed_causes.append(cause)

        return analyzed_causes

    def _generate_recommendations(
        self, probable_causes: List[Dict], combined_insights: Dict
    ) -> List[str]:
        recommendations = []

        for cause in probable_causes:
            prompt = f"""
        You are an expert system generating recommendations.
        Here is a detected cause:
        {cause}

        Please suggest a possible resolution based on experience.
        """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are OracleAgent, an expert in diagnosing system logs.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            recommendation = response.choices[0].message.content.strip()
            recommendations.append(recommendation)

        return recommendations

    def _calculate_confidence(
        self, probable_causes: List[Dict], recommendations: List[str]
    ) -> float:
        """
        Calculate a final confidence score for the recommendation system by
        combining agent signals, LLM analysis, and agreement across recommendations.
        """

        scores = []

        for i, cause in enumerate(probable_causes):
            base_score = 0.5  # default baseline

            # 🔹 1. Semantic agent confidence
            if "confidence_score" in cause:
                base_score = (base_score + cause["confidence_score"]) / 2

            # 🔹 2. Pattern analysis confidence
            if "confidence" in cause:
                base_score = (base_score + cause["confidence"]) / 2

            # 🔹 3. LLM confidence extraction (if Oracle provided one)
            llm_conf = 0.0
            if "llm_analysis" in cause:
                text = cause["llm_analysis"]
                # try to parse confidence from text like "Confidence: 0.8"
                import re

                match = re.search(r"confidence[:\s-]*([0-1](?:\.\d+)?)", text.lower())
                if match:
                    llm_conf = float(match.group(1))
                    base_score = (base_score + llm_conf) / 2

            scores.append(base_score)

        # 🔹 4. Cross-agreement: if recommendations repeat, boost confidence
        if recommendations:
            from collections import Counter

            freq = Counter(recommendations)
            max_repeated = max(freq.values())
            agreement_boost = max_repeated / len(recommendations)
            final_score = (sum(scores) / len(scores)) * (0.8 + 0.2 * agreement_boost)
        else:
            final_score = sum(scores) / len(scores) if scores else 0.5

        return round(final_score, 3)

    def _create_analysis_summary(
        self, probable_causes: List[Dict], confidence: float
    ) -> str:
        """
        Use an LLM to generate a natural analysis summary
        based on probable causes and confidence score.
        """

        if not probable_causes:
            return "No probable causes identified from the available data."

        # Format data for the LLM
        causes_text = "\n".join(
            [
                f"- {cause['cause']} (confidence: {cause['confidence']:.2f})"
                for cause in probable_causes
            ]
        )

        prompt = f"""
You are an expert system analysis assistant. 
Given the following probable causes of an error and the overall analysis confidence, 
generate a clear and concise human-readable summary.

Probable Causes:
{causes_text}

Overall Confidence: {confidence:.2f}

Guidelines:
- Summarize in 2-4 sentences.
- Highlight the most likely cause.
- Mention the number of causes identified.
- Use the confidence values to express certainty.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # keep it factual, less creative
        )

        return response.choices[0].message.content.strip()
