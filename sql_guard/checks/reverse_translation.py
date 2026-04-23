from __future__ import annotations

import json
import re

from sql_guard.checks.base import BaseCheck
from sql_guard.models import BackendResult, CheckResult

_PROMPT = """\
You are a SQL auditor. Given a natural language question and a SQL query, determine whether the SQL correctly and completely answers the question.

Question: {question}
SQL: {sql}

Respond with JSON only, no explanation or markdown:
{{"score": <float 0.0-1.0>, "reasoning": "<one sentence>", "flags": [<issue strings or empty list>]}}"""


class ReverseTranslationCheck(BaseCheck):
    name = "reverse_translation"

    def __init__(self, ollama_config) -> None:
        self._cfg = ollama_config

    def run(self, question, backend_result, backend, config) -> CheckResult:
        try:
            response = self._call_ollama(
                _PROMPT.format(question=question, sql=backend_result.sql)
            )
            score = float(response.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            reasoning = response.get("reasoning", "")
            flags = response.get("flags", [])
            return CheckResult(
                check_name=self.name,
                passed=score >= 0.7,
                score=round(score, 4),
                detail=reasoning,
                flags=[str(f) for f in flags],
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name,
                passed=False,
                score=0.5,
                detail=f"LLM judge unavailable: {e}",
                flags=["llm_judge_error"],
            )

    def _call_ollama(self, prompt: str) -> dict:
        import ollama  # lazy import — only required if this check runs

        response = ollama.chat(
            model=self._cfg.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        content = response["message"]["content"]
        return self._safe_parse(content)

    def _safe_parse(self, content: str) -> dict:
        # Strip markdown fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content.strip())
        return json.loads(content)
