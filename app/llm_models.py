from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Creator Agent Model
creator_llm = ChatOpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key="dummy",
    default_headers={
        "Authorization": "Bearer dummy",
        "User-Agent": "python-requests"
    },
    model="gpt-oss:latest",
    temperature=0,
    max_retries=2,
)
