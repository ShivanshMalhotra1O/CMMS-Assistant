import os
from typing import List, Dict, Literal
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# =========================
# OpenAI Model
# =========================

from openai import OpenAI

class OpenAIModel:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 300
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

# =========================
# Hugging Face API Model
# =========================

# from huggingface_hub import InferenceClient

# class HuggingFaceAPIModel:
#     def __init__(self, model_name: str):
#         token = os.getenv("HF_TOKEN")
#         if not token:
#             raise RuntimeError("HF_TOKEN not set")

#         self.client = InferenceClient(
#             model=model_name,
#             token=token
#         )

#     def chat(
#         self,
#         messages: List[Dict[str, str]],
#         temperature: float = 0.3,
#         max_tokens: int = 300
#     ) -> str:
#         response = self.client.chat_completion(
#             messages=messages,
#             temperature=temperature,
#             max_tokens=max_tokens
#         )
#         return response.choices[0].message.content

# =========================
# Local Host Models
# =========================

class LocalHostModel:
    def __init__(self, model_name: str = "gpt-oss:latest"):
        base_url = os.getenv("LLM_BASE_URL")
        if not base_url:
            raise RuntimeError("LLM_BASE_URL not set")

        self.client = OpenAI(
            base_url=base_url,
            api_key=os.getenv("LLM_API_KEY", "dummy")
        )
        self.model_name = model_name

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 300,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

def get_model(
    provider: Literal["openai", "hf_api","local_host"],
    model_name: str
):
    if provider == "openai":
        return OpenAIModel(model_name=model_name)

    if provider == "local_host":
        return LocalHostModel(model_name=model_name)


    # if provider == "hf_api":
    #     return HuggingFaceAPIModel(model_name=model_name)

    raise ValueError(f"Unknown provider: {provider}")

