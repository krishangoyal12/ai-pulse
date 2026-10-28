"""Thin wrapper around the LLM used to score open-ended answers.

AI_MODE=mock  -> returns canned responses from data/mock_ai_responses.json
AI_MODE=live  -> calls an OpenAI-compatible chat completions endpoint
"""
import hashlib
import json
import os

import httpx

from ..config import AI_MODE, LLM_API_URL, LLM_API_KEY, LLM_MODEL

_MOCK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_ai_responses.json")

PROMPT = """You are scoring how well an employee uses AI at work.
Rubric: 1 = no AI use, 2 = occasional basic use, 3 = regular use for simple tasks,
4 = regular, thoughtful use with review of outputs, 5 = advanced use that changes how the work is done.
Flag risks using only these labels: customer_data_shared, confidential_data_shared, unreviewed_output, policy_unaware.
Answer the question: {question}
Employee's answer: {answer}
Return JSON: {{"score": <1-5>, "reason": "<one sentence>", "flags": [<labels>]}}"""


def _mock(answer: str) -> str:
    with open(_MOCK_PATH) as f:
        canned = json.load(f)
    idx = int(hashlib.md5(answer.encode()).hexdigest(), 16) % len(canned)
    return canned[idx]


def score_answer(question: str, answer: str) -> str:
    """Returns the raw text the model produced, with robust fallback on network/API errors."""
    if AI_MODE == "mock":
        return _mock(answer)

    # Validate live mode configuration
    if not LLM_API_URL or not LLM_API_KEY:
        # Graceful fallback to mock if live mode credentials are not configured
        return _mock(answer)

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL or "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert AI governance evaluator. You strictly return compact, valid JSON conforming to the requested schema without markdown or introductory commentary.",
            },
            {"role": "user", "content": PROMPT.format(question=question, answer=answer)},
        ],
        "temperature": 0.2,
    }

    try:
        r = httpx.post(
            LLM_API_URL,
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        # Fallback to mock response if remote LLM call fails (e.g. timeout, quota, connection error)
        # Prevents employee survey submission from failing with 500 error
        return _mock(answer)


DRAFT_QUESTION_PROMPT = """You are an AI governance specialist drafting a diagnostic assessment question for employees at work.
Job Role: {job_role}
Seniority: {seniority}
Topic Focus: {topic}

Create a single thoughtful diagnostic scenario question that tests if the employee uses AI responsibly and effectively.
Provide 4-5 multiple choice options that range from beginner (1 point) to advanced/safe (5 points).

Return strictly compact JSON matching this schema:
{{
  "id": "gen-{job_role}-custom",
  "type": "mcq",
  "text": "<Question text presenting a realistic work scenario>",
  "options": [
    {{"text": "<Option 1 description>", "points": 1}},
    {{"text": "<Option 2 description>", "points": 2}},
    {{"text": "<Option 3 description>", "points": 3}},
    {{"text": "<Option 4 description>", "points": 4}},
    {{"text": "<Option 5 description>", "points": 5}}
  ]
}}"""


def draft_diagnostic_question(job_role: str, seniority: str, topic: str = "security and productivity") -> dict:
    """Uses LLM to draft a role-specific diagnostic question."""
    fallback = {
        "id": f"gen-{job_role}-fallback",
        "type": "mcq",
        "text": f"When using AI tools in your day-to-day {job_role} tasks, how do you verify accuracy and data confidentiality?",
        "options": [
            {"text": "I trust the AI output directly without verification", "points": 1},
            {"text": "I skim the output for obvious mistakes", "points": 2},
            {"text": "I check facts against internal documentation", "points": 3},
            {"text": "I test outputs thoroughly and redact all internal data", "points": 4},
            {"text": "Our team has a standardized peer review & data sanitization checklist", "points": 5},
        ],
    }

    if AI_MODE == "mock" or not LLM_API_URL or not LLM_API_KEY:
        return fallback

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL or "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You strictly output compact, valid JSON conforming to the requested schema. No code fences, no introductory remarks.",
            },
            {
                "role": "user",
                "content": DRAFT_QUESTION_PROMPT.format(job_role=job_role, seniority=seniority, topic=topic),
            },
        ],
        "temperature": 0.4,
    }

    try:
        r = httpx.post(LLM_API_URL, headers=headers, json=payload, timeout=20.0)
        r.raise_for_status()
        raw_text = r.json()["choices"][0]["message"]["content"].strip()
        # Clean any accidental markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(raw_text)
    except Exception:
        return fallback


SUITE_PROMPT = """You are an enterprise AI Governance Director creating a professional 4-question AI diagnostic assessment for a company.
Job Role: {job_role}
Seniority: {seniority}

Generate exactly 4 cohesive diagnostic questions tailored specifically to this role:
1. One Multiple Choice Question assessing tool usage frequency & daily workflow adoption.
2. One Multiple Choice Question assessing customer PII, secrets, and data confidentiality handling.
3. One Multiple Choice Question assessing human-in-the-loop review, testing, and hallucination verification.
4. One Open-Ended Question asking the employee to describe a real scenario where they used AI in their work.

Format Requirements:
- For MCQ questions, provide 4 to 5 realistic options with point ratings from 1 (poor/unsafe) to 5 (advanced/safe).
- Keep wording natural, clean, and professional. Do NOT use emojis or placeholder marks.

Return strictly compact JSON matching this exact schema:
[
  {{
    "id": "dyn-{job_role}-freq",
    "type": "mcq",
    "text": "<Question text>",
    "options": [
      {{"text": "<Option text>", "points": 1}},
      {{"text": "<Option text>", "points": 2}},
      {{"text": "<Option text>", "points": 3}},
      {{"text": "<Option text>", "points": 4}},
      {{"text": "<Option text>", "points": 5}}
    ]
  }},
  {{
    "id": "dyn-{job_role}-privacy",
    "type": "mcq",
    "text": "<Question text>",
    "options": [
      {{"text": "<Option text>", "points": 1}},
      {{"text": "<Option text>", "points": 2}},
      {{"text": "<Option text>", "points": 3}},
      {{"text": "<Option text>", "points": 4}},
      {{"text": "<Option text>", "points": 5}}
    ]
  }},
  {{
    "id": "dyn-{job_role}-review",
    "type": "mcq",
    "text": "<Question text>",
    "options": [
      {{"text": "<Option text>", "points": 1}},
      {{"text": "<Option text>", "points": 2}},
      {{"text": "<Option text>", "points": 3}},
      {{"text": "<Option text>", "points": 4}},
      {{"text": "<Option text>", "points": 5}}
    ]
  }},
  {{
    "id": "dyn-{job_role}-open",
    "type": "open",
    "text": "Describe a work task where you used AI in the last two weeks. What did you do, and what happened?"
  }}
]"""


def generate_role_diagnostic_suite(job_role: str, seniority: str) -> list[dict]:
    """Generates a complete 5-question diagnostic suite (4 MCQ + 1 open-ended) using live LLM."""
    if AI_MODE != "live" or not LLM_API_URL or not LLM_API_KEY:
        return []

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL or "qwen/qwen3.8-27b",
        "messages": [
            {
                "role": "system",
                "content": "You strictly output a compact valid JSON array of 5 diagnostic questions (4 mcq, 1 open-ended). No markdown code fences.",
            },
            {
                "role": "user",
                "content": f"Generate 5 diagnostic questions for job role: {job_role}, seniority: {seniority}. Include exactly: 1) Tool Adoption & Workflow Frequency (mcq), 2) Data Privacy & PII Protection (mcq), 3) Output Verification & Review Process (mcq), 4) Role Specific AI Scenario (mcq), and 5) Open-ended reflection asking to describe a recent work task where they used AI. Format: [{{'id':'dyn-{job_role}-freq','type':'mcq','text':'...','options':[{{'text':'...','points':1}},{{'text':'...','points':3}},{{'text':'...','points':5}}]}},{{'id':'dyn-{job_role}-privacy','type':'mcq','text':'...','options':[{{'text':'...','points':1}},{{'text':'...','points':3}},{{'text':'...','points':5}}]}},{{'id':'dyn-{job_role}-review','type':'mcq','text':'...','options':[{{'text':'...','points':1}},{{'text':'...','points':3}},{{'text':'...','points':5}}]}},{{'id':'dyn-{job_role}-scenario','type':'mcq','text':'...','options':[{{'text':'...','points':1}},{{'text':'...','points':3}},{{'text':'...','points':5}}]}},{{'id':'dyn-{job_role}-open','type':'open','text':'Describe a work task where you used AI in the last two weeks. What did you do, and what happened?'}}]",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
    }

    try:
        r = httpx.post(LLM_API_URL, headers=headers, json=payload, timeout=25.0)
        r.raise_for_status()
        raw_text = r.json()["choices"][0]["message"]["content"].strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        suite = json.loads(raw_text)
        if isinstance(suite, list) and len(suite) >= 4:
            return suite
    except Exception as e:
        print(f"[LLM] Dynamic suite generation fallback due to: {e}")
    return []





