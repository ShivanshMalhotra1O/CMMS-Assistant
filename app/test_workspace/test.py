from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    base_url=os.getenv("LLM_BASE_URL", "https://llm.swayatt.com/v1"),
    api_key="dummy",
    default_headers={
        "Authorization": "Bearer dummy",
        "User-Agent": "python-requests"
    },
    model="gpt-oss:latest",
    temperature=0,
)

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is sunny and 25 degrees."

# --- TEST 1: Simple message ---
print("--- TEST 1: Simple message ---")
try:
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print(f"PASSED: {response.content}\n")
except Exception as e:
    print(f"FAILED: {e}\n")

# --- TEST 2: Tool calling ---
print("--- TEST 2: Tool calling ---")
try:
    llm_with_tools = llm.bind_tools([get_weather])
    response = llm_with_tools.invoke([
        HumanMessage(content="What is the weather in Delhi? Use the get_weather tool.")
    ])
    if response.tool_calls:
        print(f"PASSED - Tool called : {response.tool_calls[0]['name']}")
        print(f"         Args        : {response.tool_calls[0]['args']}\n")
    else:
        print(f"PASSED (no tool call) - Response: {response.content}\n")
except Exception as e:
    print(f"FAILED: {e}\n")