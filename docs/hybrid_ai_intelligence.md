# Smart Subscription Advisor — Hybrid AI Architecture Document

## Overview

Smart Subscription Advisor is architected as a **Hybrid AI Intelligence** system.
Financial figures, arithmetic, and database facts remain 100% deterministic, while large language models (Groq) are employed strictly for contextual reasoning, prioritization, explanation, and natural language synthesis.

---

## 1. Audit of Current Intelligence Architecture

### A. Deterministic Calculations
The following values are strictly mathematical and deterministic:
- **Monthly Spending:** `sum(sub.monthly_cost for sub in subscriptions)`
- **Yearly Projection:** `total_monthly * 12`
- **Subscription Count:** `len(subscriptions)`
- **Category Totals & Percentages:** Aggregated from individual subscription records.
- **Renewal Dates & Countdown:** `renewal_date - today` calculated via datetime / relativedelta.
- **Health Score Number:** Base 100 with deterministic deductions based on priority (-15 for Low, -5 for Medium), usage (-10 for Rarely), and high cost (-5 for > ₹1,000).
- **Potential Savings Sum:** Exact sum of monthly costs for Low-priority and Rarely-used subscriptions.

### B. Rule-Based Recommendation Logic (`utils/recommendation_engine.py`)
- **`calculate_priority(...)`**:
  - Usage frequency scoring: Daily (30), Weekly (20), Monthly (10), Rarely (0).
  - Daily hours scoring: >=3h (25), >=2h (20), >=1h (15), >=0.5h (10).
  - Category weighting: Education/Productivity (15), Health (12), Cloud (10), Entertainment (8), etc.
  - Occupation bonus heuristics: Software Developer (+10 for Productivity), Student (+10 for Education), etc.
  - Value for money ratio: `monthly_cost / (daily_usage * 30)`.
  - Financial preference modifier: Money Saver penalties/bonuses.

### C. Rule-Based Insight Generation (`utils/insights_engine.py`)
- **`generate_insight(subscription, financial_preference)`**:
  - Computes an urgency score (score >= 120 → danger/cancel; score >= 70 → warning/review; otherwise keep).
  - Emits hardcoded template sentences.

### D. Existing Groq Chatbot (`services/chat_service.py`)
- Domain-specific assistant protected by a 50+ term deterministic keyword guardrail.
- System prompt strictly grounded on user's database records.
- User isolation enforced through JWT identity and database filtering.

---

## 2. Target Hybrid AI Architecture

```
                    +------------------------------------+
                    |        User Subscriptions          |
                    |          (Database / ORM)          |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |        Intelligence Service        |
                    |  - Deterministic Math & Totals     |
                    |  - Structured Health Score Factors |
                    |  - Recommendation Candidates       |
                    +------------------------------------+
                                      |
                         Structured Context Payload
                                      |
                                      v
                    +------------------------------------+
                    |       AI Reasoning Service         |
                    |   (Groq LLM Reasoning Layer)       |
                    +------------------------------------+
                                 /          \
                         Success              Failure / Timeout
                            /                    \
                           v                      v
                +---------------------+  +-------------------------+
                | AI Structured JSON  |  | Deterministic Rule-Based|
                | Insights & Recs     |  | Fallback Insights       |
                +---------------------+  +-------------------------+
                           \                      /
                            \                    /
                             v                  v
                    +------------------------------------+
                    |       Unified Intelligence         |
                    |       (Dashboard & Chatbot)        |
                    +------------------------------------+
```

---

## 3. Boundaries & Grounding Matrix

| Component | Responsibility Layer | Can Groq Alter? |
|---|---|:---:|
| Total Monthly / Yearly Spend | Deterministic Service | ❌ NO |
| Health Score Number (0–100) | Deterministic Service | ❌ NO |
| Health Score Factors | Deterministic Service | ❌ NO |
| Renewal Dates & Countdowns | Deterministic Service | ❌ NO |
| Recommendation Candidates | Rule-Based Signals Engine | ❌ NO |
| Insight Prioritization & Ranking | Groq AI Reasoning | ✅ YES |
| Personalized Explanations | Groq AI Reasoning | ✅ YES |
| Contextual Advice & Trade-offs | Groq AI Reasoning | ✅ YES |
| Natural Language Synthesis | Groq AI Reasoning | ✅ YES |
