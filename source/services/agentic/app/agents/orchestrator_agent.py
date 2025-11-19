from app.agents.agent_base import AgentBase
from app.agents.documentalist_agent import documentalist_agent
from app.agents.web_search_agent import web_search_agent
from langchain.tools.render import render_text_description
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langfuse.decorators import langfuse_context, observe


class OrchestratorAgent(AgentBase):
    def _get_available_tools(self) -> list[callable]:
        @tool
        async def ask_documentalist(question: str):
            """
            Consult the documentalist agent to retrieve factual information from the internal Supabase knowledge base.
            """
            return await documentalist_agent.send_message(question)

        @tool
        async def ask_web_search(question: str):
            """
            Consult the web search agent to gather up-to-date information from approved public sources.
            """
            return await web_search_agent.send_message(question)

        return [ask_documentalist, ask_web_search]

    @observe(as_type="generation")
    async def send_message(self, original_question: str, reformulated_query: str) -> str:
        llm = await self._create_openai_llm()
        tool_descriptions = render_text_description(self.AVAILABLE_TOOLS)

        messages = [
            SystemMessage(
                content=(
                    "You are the orchestrator agent for the Pole Universitaire Leonard de Vinci (ESILV, EMLV, IIM) in "
                    "Paris La Defense. Combine insights from specialized agents to craft answers strictly about this "
                    "campus, its programs, services, and student life. Use the provided tools whenever more context is "
                    "required, and ignore topics unrelated to the Pole. Always gather enough evidence before finalizing "
                    "an answer. When responding to the user, be clear, cite the origin of facts (e.g., question ids or "
                    "URLs tied to pulv.fr/emlv.fr/esilv.fr), and format the response in markdown using the user's "
                    "language."
                    f"\n\nTools:\n{tool_descriptions}"
                )
            ),
            HumanMessage(
                content=(
                    "Original user question:\n"
                    f"{original_question}\n\n"
                    "Reformulated query for research:\n"
                    f"{reformulated_query}\n\n"
                    "Plan your reasoning, call the necessary tools, and then provide the final answer when ready."
                )
            ),
        ]

        llm_response = await self._llm_call_with_tools(llm, messages)
        langfuse_context.update_current_observation(name="Agent: Orchestrator")

        if isinstance(llm_response, str):
            return llm_response
        return llm_response.content


orchestrator_agent = OrchestratorAgent()
