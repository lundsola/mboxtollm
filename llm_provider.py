import logging
from typing import Optional

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    GOOGLE_API_KEY,
    GOOGLE_MODEL,
)

logger = logging.getLogger(__name__)

# --- System prompts ---

_SUMMARIZE_SYSTEM = (
    "You are an expert at analyzing email conversations. "
    "Summarize the key points, decisions, and action items. "
    "Be concise but thorough."
)

_QA_SYSTEM = (
    "You are a helpful assistant that answers questions based on email archives. "
    "Only use information from the provided emails. "
    "If the answer isn't in the emails, say so."
)

_STORYLINE_SYSTEM = (
    "You are a narrative writer specializing in reconstructing events "
    "from email archives. Create a clear, chronological storyline "
    "that reads like a report. Include dates, key people, and "
    "how events unfolded. Use a neutral, factual tone."
)


# --- Provider implementations ---


class _AnthropicProvider:
    def __init__(self, api_key: str, model: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def call(self, system: str, user_prompt: str, max_tokens: int = 2048) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text


class _OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def call(self, system: str, user_prompt: str, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content


class _GoogleProvider:
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.genai = genai
        self.model_name = model

    def call(self, system: str, user_prompt: str, max_tokens: int = 2048) -> str:
        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system,
        )
        response = model.generate_content(
            user_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text


# --- Public interface ---


def _build_provider(provider_name: str):
    """Create the appropriate LLM provider based on config."""
    name = provider_name.lower()

    if name == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        return _AnthropicProvider(ANTHROPIC_API_KEY, ANTHROPIC_MODEL)

    if name == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return _OpenAIProvider(OPENAI_API_KEY, OPENAI_MODEL)

    if name == "google":
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required for Google provider")
        return _GoogleProvider(GOOGLE_API_KEY, GOOGLE_MODEL)

    raise ValueError(
        f"Unknown LLM provider: {name!r}. Use 'anthropic', 'openai', or 'google'."
    )


class LLMProvider:
    """Multi-provider LLM integration for email summarization and Q&A."""

    def __init__(self, provider_name: Optional[str] = None):
        name = provider_name or LLM_PROVIDER
        logger.info("Initializing LLM provider: %s", name)
        self._provider = _build_provider(name)
        self.provider_name = name

    def summarize_thread(self, messages: list[dict]) -> str:
        formatted = _format_thread(messages)
        return self._provider.call(
            system=_SUMMARIZE_SYSTEM,
            user_prompt=f"Summarize this email thread:\n\n{formatted}",
        )

    def answer_question(self, question: str, context_messages: list[dict]) -> str:
        formatted = _format_thread(context_messages)
        return self._provider.call(
            system=_QA_SYSTEM,
            user_prompt=(
                f"Based on these emails:\n\n{formatted}\n\n"
                f"Question: {question}"
            ),
        )

    def generate_storyline(self, messages: list[dict], topic: str) -> str:
        formatted = _format_thread(messages)
        return self._provider.call(
            system=_STORYLINE_SYSTEM,
            user_prompt=(
                f'Create a chronological storyline about "{topic}" '
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
        if len(body) > 3000:
            body = body[:3000] + "...[truncated]"
        parts.append(f"From: {sender}\nDate: {date}\nSubject: {subject}\n\n{body}")
    return "\n\n---\n\n".join(parts)
