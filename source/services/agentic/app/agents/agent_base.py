import os
from abc import ABC
from typing import Any, Dict, List

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langfuse.decorators import langfuse_context, observe


class AgentBase(ABC):
    def __init__(self):
        self.AVAILABLE_TOOLS: list[callable] = self._get_available_tools()

    def _get_available_tools(self) -> list[callable]:
        return []

    async def _create_openai_llm(self):
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0.7,
            top_p=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    @observe(as_type="generation")
    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        langfuse_context.update_current_observation(
            name="Method: Tool Call", input={"Tool Called": tool_name, "Args": tool_args}
        )

        for selected_tool in self.AVAILABLE_TOOLS:
            if selected_tool.name == tool_name:
                try:
                    result = await selected_tool.ainvoke(tool_args)
                    return result
                except Exception as e:
                    return f"Error executing tool {tool_name}: {str(e)}"

        return f"Tool {tool_name} not found"


    @observe(as_type="generation")
    async def _llm_call_with_tools(self, llm: ChatOpenAI, messages: List):
        """Make an LLM call with tools support, handling multiple rounds of tool calls."""
        llm_with_tools = llm.bind_tools(self.AVAILABLE_TOOLS)

        # Keep processing until we get a response without tool calls
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            response = await llm_with_tools.ainvoke(messages)
            token_usage = response.usage_metadata
            usage_details = {
                "input": token_usage.get("input_tokens"),
                "output": token_usage.get("output_tokens"),
                "total": token_usage.get("total_tokens"),
            }
            langfuse_context.update_current_observation(
                name="Method: LLM Call", model=os.getenv("OPENAI_MODEL"), usage_details=usage_details
            )
            # Check if the model wants to use tools
            if hasattr(response, "tool_calls") and response.tool_calls and len(response.tool_calls) > 0:
                # Add the AI response to messages
                messages.append(response)

                # Process each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    # Execute the tool
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # Add tool result to messages
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))

                iteration += 1
            else:
                # No tool calls, we have our final response
                return response
        # If we hit max iterations, return the last response anyway
        # This prevents infinite loops
        return response
