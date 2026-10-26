"""Calls Gemini through LangChain. Every method returns None if anything goes wrong, so the app can use templates."""
import json
import re

from core.config import settings


class LLM:
    def __init__(self) -> None:
        self.provider = "gemini" if settings.gemini_api_key else "mock"
        self.last_error = ""
        self._model = None

    @property
    def available(self) -> bool:
        return self.provider != "mock"

    def complete(self, system: str, prompt: str) -> str | None:
        if not self.available:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            if self._model is None:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._model = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key, temperature=0.4, timeout=45)
            content = self._model.invoke([SystemMessage(content=system), HumanMessage(content=prompt)]).content
            if isinstance(content, list):  # newer models return a list of parts
                content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
            self.last_error = ""
            return str(content).strip() or None
        except Exception as exc:  # noqa: BLE001  (any AI problem means: use the template instead)
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            return None

    def json(self, system: str, prompt: str) -> dict | None:
        text = self.complete(system + "\nReply with one valid JSON object only.", prompt)
        match = re.search(r"\{.*\}", text or "", re.S)
        try:
            return json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            return None


llm = LLM()
