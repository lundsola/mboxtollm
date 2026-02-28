import logging
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


class LLMProvider:
    """Anthropic Claude integration for email summarization and Q&A."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key or ANTHROPIC_API_KEY
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Set it in your environment or .env file."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model or ANTHROPIC_MODEL

    def _call(self, system: str, user_prompt: str, max_tokens: int = 2048) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def summarize_thread(self, messages: list[dict]) -> str:
        """Summarize an email conversation thread."""
        formatted = _format_thread(messages)
        return self._call(
            system=(
                "You are an expert at analyzing email conversations. "
                "Summarize the key points, decisions, and action items. "
                "Be concise but thorough."
            ),
            user_prompt=f"Summarize this email thread:\n\n{formatted}",
        )

    def answer_question(self, question: str, context_messages: list[dict]) -> str:
        """Answer a question using email context (RAG)."""
        formatted = _format_thread(context_messages)
        return self._call(
            system=(
                "You are a helpful assistant that answers questions based on email archives. "
                "Only use information from the provided emails. "
                "If the answer isn't in the emails, say so."
            ),
            user_prompt=(
                f"Based on these emails:\n\n{formatted}\n\n"
                f"Question: {question}"
            ),
        )

    def generate_storyline(self, messages: list[dict], topic: str) -> str:
        """Generate a narrative timeline from emails related to a topic."""
        formatted = _format_thread(messages)
        return self._call(
            system=(
                "You are a narrative writer specializing in reconstructing events "
                "from email archives. Create a clear, chronological storyline "
                "that reads like a report. Include dates, key people, and "
                "how events unfolded. Use a neutral, factual tone."
            ),
            user_prompt=(
                f"Create a chronological storyline about \"{topic}\" "
                f"based on these emails:\n\n{formatted}"
            ),
            max_tokens=4096,
        )


def _format_thread(messages: list[dict]) -> str:
    """Format messages into a readable thread for LLM context."""
    parts = []
    for msg in messages:
        date = msg.get("date", "unknown date")
        sender = msg.get("from", "unknown sender")
        subject = msg.get("subject", "(no subject)")
        body = msg.get("cleaned_body") or msg.get("body", "")
        # Truncate very long bodies to fit context window
        if len(body) > 3000:
            body = body[:3000] + "...[truncated]"
        parts.append(f"From: {sender}\nDate: {date}\nSubject: {subject}\n\n{body}")
    return "\n\n---\n\n".join(parts)
