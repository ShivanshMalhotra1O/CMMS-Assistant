import logging
from openai import OpenAI
import os

logger = logging.getLogger(__name__)


def warmup_llm():
    """
    Sends a tiny hidden request to warm up the LLM.
    This is NOT user-visible.
    """
    try:
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY", "dummy"),
        )

        logger.info("Warming up LLM...")

        client.chat.completions.create(
            model="qwen2.5:7b",
            messages=[
                {"role": "user", "content": "ping"}
            ],
            max_tokens=1,
            temperature=0.0,
        )

        logger.info("LLM warm-up completed successfully")

    except Exception as e:
        logger.warning(f"LLM warm-up failed: {e}")
