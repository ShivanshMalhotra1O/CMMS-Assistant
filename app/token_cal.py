import json
import time
from langchain_core.messages import ToolMessage


def track_tokens_and_invoke(llm_with_tools, messages, tool_map, max_iterations=5):
    """Execute LLM invocations with tool calls and track token usage."""
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    for i in range(max_iterations):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            print(f"Error on iteration {i + 1}: {e}")
            raise

        usage = response.response_metadata.get("token_usage") or response.response_metadata.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        print(f"[Iteration {i+1}] Tokens — input: {input_tokens} | output: {output_tokens} | cumulative: {total_input_tokens + total_output_tokens}")

        messages.append(response)

        if not response.tool_calls:
            print("\n" + "=" * 70)
            print("FINAL:")
            print(response.content)
            print("=" * 70)
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            print(f"\n>>> Calling tool : {tool_name}")
            print(f"    Args         : {json.dumps(tool_args, default=str)}")

            result = tool_map[tool_name].invoke(tool_args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call['id']))
            print(f"    Result       : {json.dumps(result, indent=2, default=str)}")

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n{'=' * 70}")
    print(f"TOKEN USAGE SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total input tokens  : {total_input_tokens}")
    print(f"  Total output tokens : {total_output_tokens}")
    print(f"  Total tokens        : {total_input_tokens + total_output_tokens}")
    print(f"  Time taken          : {total_time:.2f} seconds")
    print(f"{'=' * 70}")

    return total_input_tokens, total_output_tokens, total_time
