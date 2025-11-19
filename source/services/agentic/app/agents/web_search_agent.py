import asyncio

from app.agents.agent_base import AgentBase
from langchain.tools.render import render_text_description
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langfuse.decorators import langfuse_context, observe


class WebSearchAgent(AgentBase):
    def _get_available_tools(self) -> list[callable]:
        @tool
        async def web_search(query: str):
            """
            Perform a Tavily web search to gather up-to-date information from esilv.fr, emlv.fr, or the PULV website.
            """
            results = await asyncio.to_thread(
                TavilySearchResults(max_results=5).run,
                query,
            )
            return results

        return [web_search]

    @observe(as_type="generation")
    async def send_message(self, reformulated_query: str) -> str:
        llm = await self._create_openai_llm()
        tool_descriptions = render_text_description(self.AVAILABLE_TOOLS)
        messages = [
            SystemMessage(
                content=(
                    "You are the web search agent for the Pole Universitaire Leonard de Vinci (ESILV, EMLV, IIM). Use "
                    "the available Tavily tool to research the request exclusively through reliable sources tied to the "
                    "Pole (esilv.fr, emlv.fr, iim.fr, pulv.fr or other official properties). Consolidate findings into a "
                    "concise report with URLs when possible, keep the response in the user's language, and ignore "
                    "results unrelated to the campus or its three schools."
                    f"\n\nTools:\n{tool_descriptions}"
                )
            ),
            HumanMessage(content=reformulated_query),
        ]

        llm_response = await self._llm_call_with_tools(llm, messages)
        langfuse_context.update_current_observation(name="Agent: Web Searcher")

        if isinstance(llm_response, str):
            return llm_response
        return llm_response.content


web_search_agent = WebSearchAgent()
