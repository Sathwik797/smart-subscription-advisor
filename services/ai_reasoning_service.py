"""AI reasoning service: provides contextual reasoning, explanations, and personalized insights.

Architecture:
Database -> Repository -> Existing Services -> Intelligence Service -> AI Reasoning Service -> Groq

Features:
- Never calculates financial facts (receives grounded facts from IntelligenceService).
- Calls Groq once with strict JSON schema instructions.
- Validates model output and gracefully falls back to deterministic rule-based insights on any failure.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

from groq import APIConnectionError, APIError, APITimeoutError, Groq

from logging_config.logger import logger
from services.intelligence_service import intelligence_service

_AI_SYSTEM_PROMPT = """You are the AI Intelligence Reasoning Layer of Smart Subscription Advisor.
Your job is to interpret the user's deterministic subscription facts and analytical signals, then synthesize concise, personalized, natural-language insights and prioritized recommendations.

STRICT GROUNDING RULES:
1. Use ONLY the provided financial context. Never invent subscriptions, costs, renewal dates, or facts.
2. DO NOT recalculate totals or numbers — use the exact numbers supplied.
3. Format all currency in Indian Rupees (₹), e.g. ₹649.00.
4. Return ONLY a valid JSON object matching the schema below. Do NOT include markdown code blocks, backticks, or preamble.

REQUIRED JSON SCHEMA:
{
  "insights": [
    {
      "title": "Short punchy title",
      "message": "Clear 1-2 sentence personalized explanation grounded strictly in the data.",
      "priority": "high" | "medium" | "low",
      "category": "savings" | "renewal" | "health" | "category"
    }
  ],
  "recommendations": [
    {
      "title": "Actionable recommendation title",
      "reason": "Why this recommendation is suggested based on usage/cost data.",
      "estimated_monthly_savings": number (0 if not applicable),
      "action": "cancel" | "review" | "keep" | "optimize",
      "color": "danger" | "warning" | "success" | "info"
    }
  ]
}

--- USER SUBSCRIPTION CONTEXT ---
{context_json}
--- END CONTEXT ---
"""


class AIReasoningService:
    """Orchestrates LLM reasoning on top of deterministic subscription intelligence context."""

    def __init__(self):
        self.intelligence_service = intelligence_service

    def _build_fallback_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a reliable, deterministic fallback response from rule-based candidates.

        Used when Groq is unconfigured, unavailable, times out, or returns invalid data.
        """
        candidates = context.get("recommendation_candidates", [])
        health = context.get("health_score", {})
        summary = context.get("financial_summary", {})

        insights: List[Dict[str, Any]] = []
        recommendations: List[Dict[str, Any]] = []

        # 1. Health Score Insight
        score = health.get("score", 100)
        if score >= 80:
            insights.append({
                "title": "Strong Subscription Health",
                "message": f"Your subscription health score is {score}/100. Your recurring spending aligns well with your usage.",
                "priority": "low",
                "category": "health",
            })
        elif score >= 50:
            insights.append({
                "title": "Optimization Potential",
                "message": f"Your subscription health score is {score}/100. Reviewing rarely used or lower priority services can help improve it.",
                "priority": "medium",
                "category": "health",
            })
        else:
            insights.append({
                "title": "Attention Recommended",
                "message": f"Your subscription health score is {score}/100 with multiple high-cost or low-usage services detected.",
                "priority": "high",
                "category": "health",
            })

        # 2. Savings Insight if available
        potential_savings = summary.get("potential_monthly_savings", 0.0)
        if potential_savings > 0:
            insights.append({
                "title": "Identified Savings Opportunity",
                "message": f"You could potentially save up to ₹{potential_savings:.2f}/month by optimizing underutilized subscriptions.",
                "priority": "high",
                "category": "savings",
            })

        # 3. Rule-based recommendations
        for candidate in candidates[:3]:
            recommendations.append({
                "title": f"Review {candidate.get('subscription', 'Subscription')}" if candidate.get("subscription") else "Review Category",
                "reason": candidate.get("reason", "Review subscription value."),
                "estimated_monthly_savings": candidate.get("estimated_savings", 0.0),
                "action": "cancel" if candidate.get("color") == "danger" else "review",
                "color": candidate.get("color", "warning"),
            })

        return {
            "source": "deterministic_fallback",
            "insights": insights,
            "recommendations": recommendations,
        }

    def _validate_ai_payload(self, parsed: Dict[str, Any]) -> bool:
        """Validate that the AI returned the expected JSON schema structure."""
        if not isinstance(parsed, dict):
            return False
        if "insights" not in parsed or "recommendations" not in parsed:
            return False
        if not isinstance(parsed["insights"], list) or not isinstance(parsed["recommendations"], list):
            return False

        for ins in parsed["insights"]:
            if not isinstance(ins, dict) or "title" not in ins or "message" not in ins:
                return False

        for rec in parsed["recommendations"]:
            if not isinstance(rec, dict) or "title" not in rec or "reason" not in rec:
                return False

        return True

    def _call_groq_reasoning(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call Groq LLM with strictly grounded context and parse JSON response."""
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "groq/compound-mini")

        if not api_key:
            logger.info("GROQ_API_KEY is not configured — using deterministic intelligence fallback.")
            return None

        # Minimize context payload size (exclude raw internal IDs)
        clean_context = {
            "financial_summary": context.get("financial_summary"),
            "categories": context.get("categories"),
            "renewals": context.get("renewals"),
            "health_score": context.get("health_score"),
            "recommendation_candidates": context.get("recommendation_candidates"),
            "today": context.get("today"),
        }

        context_json_str = json.dumps(clean_context, indent=2)
        system_prompt = _AI_SYSTEM_PROMPT.replace("{context_json}", context_json_str)

        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Analyze my subscription profile and provide prioritized insights and actionable recommendations in JSON format."},
                ],
                temperature=0.2,
                max_tokens=900,
                timeout=15,
            )

            raw_text = completion.choices[0].message.content.strip()

            # Clean reasoning tags if any
            if "<think>" in raw_text and "</think>" in raw_text:
                raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

            # Strip markdown json codeblocks if returned
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            parsed = json.loads(raw_text)

            if self._validate_ai_payload(parsed):
                parsed["source"] = "groq_ai"
                return parsed

            logger.warning("Groq AI returned payload that failed schema validation — activating fallback.")
            return None

        except (APITimeoutError, APIConnectionError, APIError) as exc:
            logger.warning("Groq API unavailable for hybrid intelligence (%s) — activating fallback.", exc.__class__.__name__)
            return None
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to parse Groq AI intelligence response (%s) — activating fallback.", exc.__class__.__name__)
            return None

    def get_reasoned_intelligence(self, user: Any) -> Dict[str, Any]:
        """
        Public entrypoint: Generate hybrid intelligence for the authenticated user.

        1. Builds deterministic facts and analytical signals.
        2. Tries Groq for personalized contextual reasoning.
        3. If Groq fails for ANY reason, seamlessly returns deterministic fallback.
        """
        # Step 1: Deterministic facts (strict user isolation)
        context = self.intelligence_service.build_intelligence_context(user)

        # If user has no subscriptions, return a clean empty profile immediately
        if context["financial_summary"]["active_subscriptions"] == 0:
            return {
                "context": context,
                "intelligence": {
                    "source": "deterministic_empty",
                    "insights": [{
                        "title": "No Active Subscriptions",
                        "message": "You haven't added any subscriptions yet. Add your recurring services to unlock personalized insights and spending analysis.",
                        "priority": "low",
                        "category": "health",
                    }],
                    "recommendations": [],
                },
            }

        # Step 2: Attempt AI reasoning
        ai_result = self._call_groq_reasoning(context)

        # Step 3: Fallback if needed
        final_intelligence = ai_result if ai_result is not None else self._build_fallback_output(context)

        return {
            "context": context,
            "intelligence": final_intelligence,
        }


ai_reasoning_service = AIReasoningService()
