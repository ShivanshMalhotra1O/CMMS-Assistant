from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from app.llm_models import creator_llm
from app.registry.registry_loader import load_registry
import re
import sys
import json

sys.path.append('./app/test_workspace')
from app.agents.retrieval.retrieval_tools.retrieval_tools import (
    get_work_orders,
    get_assets,
    get_users
)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def clean_prompt(text: str) -> str:
    """Remove non-ASCII characters."""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


def execute_tool_call(tool_call: dict, tool_map: dict) -> str:
    """Execute a single tool call and return the result as a JSON string."""
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name].invoke(tool_args)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def log_token_usage(response: AIMessage):
    """Log token usage from the LLM response if available."""
    usage = (
        getattr(response, "usage_metadata", None)
        or getattr(response, "response_metadata", {}).get("usage", None)
    )
    if usage:
        print(f"DEBUG: Tokens — input: {usage.get('input_tokens', '?')}, "
              f"output: {usage.get('output_tokens', '?')}")


# ─────────────────────────────────────────
# Setup
# ─────────────────────────────────────────

registry = load_registry('./app/registry/retrieval_registry.yaml')

llm = creator_llm

tools = [
    get_work_orders,
    get_assets,
    get_users
]

tool_map = {t.name: t for t in tools}

retrieval_prompt = registry['retrieval_operations']['system_prompt']

MAX_ITERATIONS = 10  # Safety cap to prevent infinite loops


# ─────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────

def run_retrieval_agent(llm, user_input: str) -> str:
    """
    Run the retrieval agent with a multi-turn agentic loop.

    The LLM can call multiple tools across multiple turns — chaining
    tool calls to resolve join-like queries (e.g. work orders + asset details)
    without any hardcoded aggregation logic.

    Returns the final text response from the LLM.
    """
    active_prompt = clean_prompt(retrieval_prompt)

    # KEY FIX: bind_tools on the LLM directly — do NOT pass through
    # track_tokens_and_invoke because that function swallows the AIMessage
    # and handles tool execution internally, breaking the agentic loop.
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=active_prompt),
        HumanMessage(content=user_input)
    ]

    print(f"\nDEBUG: System prompt length : {len(active_prompt)} chars")
    print(f"DEBUG: Tools bound          : {len(tools)}")
    print(f"DEBUG: User input           : {user_input}\n")

    for iteration in range(MAX_ITERATIONS):
        print(f"DEBUG: ── Iteration {iteration + 1} ──────────────────")

        # Invoke LLM directly to get the raw AIMessage back.
        # tool_calls live on this object — if we don't get it back, the loop breaks.
        response = llm_with_tools.invoke(messages)
        log_token_usage(response)

        # Append assistant turn to history
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None)

        # No tool calls → LLM is done, return final text answer
        if not tool_calls:
            print(f"\nDEBUG: Final response after {iteration + 1} iteration(s).\n")
            return response.content

        # Execute every tool call in this turn and feed results back
        print(f"DEBUG: Tool calls this turn: {[tc['name'] for tc in tool_calls]}")

        for tool_call in tool_calls:
            tool_result = execute_tool_call(tool_call, tool_map)

            print(f"DEBUG:   ✓ {tool_call['name']}({tool_call['args']}) "
                  f"→ {len(tool_result)} chars returned")

            messages.append(
                ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call["id"]
                )
            )

    # Safety fallback if max iterations are exhausted
    print(f"DEBUG: Max iterations ({MAX_ITERATIONS}) reached.")
    return "I was unable to complete the query within the allowed steps. Please try a simpler query."


# ─────────────────────────────────────────
# Standalone entry point
# ─────────────────────────────────────────

if __name__ == "__main__":
    from app.llm_models import creator_llm
    user_input = input("Enter your request: ")
    answer = run_retrieval_agent(creator_llm, user_input)
    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)