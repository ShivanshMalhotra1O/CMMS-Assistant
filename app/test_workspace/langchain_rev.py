from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import os
from dotenv import load_dotenv
import yaml
import sys
import json
sys.path.append('./app/test_workspace')
from create_wo_tool import asset_information, get_past_work_orders, work_order_counter, get_technician_details, create_work_order

load_dotenv()

# Loading Registry
def load_registry(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

registry = load_registry('./app/test_workspace/test_registry.yaml')

# Model
MODEL_NAME = "gpt-oss:latest"

llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY", "dummy"),
    temperature=0,
)

# System Prompt - Router
system_prompt = """You are an intelligent CMMS assistant.

If user input contains keywords related to "work order" (e.g., "create work order", "work order for", "new work order"):
- Follow the work order system prompt from registry
- Execute work order creation process

Otherwise:
- Respond to general queries about CMMS operations
"""

# Get work order specific prompt from registry
work_order_prompt = registry['workorder_operations']['create_workorder']['system_prompt']

# Tools
tools = [asset_information, get_past_work_orders, work_order_counter, get_technician_details, create_work_order]
llm_with_tools = llm.bind_tools(tools)

# Invoke with agent loop
user_input = input("Enter your request: ")

# Check if work order related
if any(keyword in user_input.lower() for keyword in ['work order', 'workorder', 'wo']):
    active_prompt = work_order_prompt
else:
    active_prompt = system_prompt

messages = [HumanMessage(content=active_prompt + "\n\nUser: " + user_input)]

for i in range(5):
    response = llm_with_tools.invoke(messages)
    messages.append(response)
    
    if not response.tool_calls:
        print("\n" + "="*70)
        print("FINAL:")
        print(response.content)
        print("="*70)
        break
    
    for tool_call in response.tool_calls:
        tool_map = {
            'asset_information': asset_information,
            'get_past_work_orders': get_past_work_orders,
            'work_order_counter': work_order_counter,
            'get_technician_details': get_technician_details,
            'create_work_order': create_work_order
        }
        
        result = tool_map[tool_call['name']].invoke(tool_call['args'])
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call['id']))

print(f"\n{tool_call['name']}: {json.dumps(result, indent=2, default=str)}")
