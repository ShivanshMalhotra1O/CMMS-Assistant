from langchain_core.messages import HumanMessage, SystemMessage
from app.llm_models import creator_llm 
from app.registry.registry_loader import load_registry
from app.token_cal import track_tokens_and_invoke
import re
import sys


sys.path.append('./app/test_workspace')
from app.agents.creator.create_tools.create_wo_tool import (
    asset_information,
    get_past_work_orders,
    work_order_counter,
    get_technician_details,
    create_work_order
)


def clean_prompt(text: str) -> str:
    """Remove non-ASCII characters."""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


registry = load_registry('./app/registry/creator_registry.yaml')

llm = creator_llm

tools = [
    asset_information,
    get_past_work_orders,
    work_order_counter,
    get_technician_details,
    create_work_order
]

tool_map = {t.name: t for t in tools}

system_prompt = "You are an intelligent CMMS assistant. Answer general queries about CMMS operations."
work_order_prompt = registry['workorder_operations']['create_workorder']['system_prompt']

def run_create_agent(llm, user_input: str):
    """Run the work order creation agent."""
    active_prompt = clean_prompt(work_order_prompt)
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
    run_create_agent(creator_llm, user_input)