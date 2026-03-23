from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from app.llm_models import creator_llm 
from app.registry.registry_loader import load_registry
from app.token_cal import track_tokens_and_invoke
import re
import sys
import json
import yaml


sys.path.append('./app/test_workspace')
from app.agents.retrieval.retrieval_tools.retrieval_tools import (
    get_work_orders,
    get_assets,
)


def clean_prompt(text: str) -> str:
    """Remove non-ASCII characters."""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


registry = load_registry('./app/registry/retrieval_registry.yaml')

llm = creator_llm

tools = [
    get_work_orders,
    get_assets
]

tool_map = {t.name: t for t in tools}

system_prompt = "You are an intelligent CMMS assistant. Answer general queries about CMMS operations."

retrieval_prompt = registry['retrieval_operations']['system_prompt']

def run_retrieval_agent(llm, user_input: str):
    """Run the retrieval agent."""
    active_prompt = clean_prompt(retrieval_prompt)
    llm_with_tools = llm.bind_tools(tools)
 
    messages = [
        SystemMessage(content=active_prompt),
        HumanMessage(content=user_input)
    ]
 
    print(f"DEBUG: System prompt length : {len(active_prompt)} chars")
    print(f"DEBUG: Tools bound          : {len(tools)}\n")
 
    track_tokens_and_invoke(llm_with_tools, messages, tool_map)
 
 
# Run standalone if called directly
if __name__ == "__main__":
    from app.llm_models import creator_llm
    user_input = input("Enter your request: ")
    run_retrieval_agent(creator_llm, user_input)
 