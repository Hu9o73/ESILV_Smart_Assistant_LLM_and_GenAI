from app.agents.agent_base import AgentBase
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse.decorators import langfuse_context, observe


class QueryReformulatorAgent(AgentBase):
    def _get_available_tools(self) -> list[callable]:
        return []

    @observe(as_type="generation")
    async def send_message(self, user_message: str) -> str:
        """Produce a concise reformulation of the original user query."""
        llm = await self._create_openai_llm()
        messages = [
            SystemMessage(
                content=(
                    "You are a query reformulation specialist dedicated to the Pole Universitaire Leonard de Vinci in "
                    "Paris La Defense, which regroups the ESILV, EMLV, and IIM schools. Rewrite the user's question so it "
                    "is clear, self-contained, factual, and focused on this campus ecosystem. Preserve the original "
                    "language, include every important constraint, filter out topics unrelated to the Pole, and do not "
                    "answer the question."
                )
            ),
            HumanMessage(content=user_message),
        ]

        llm_response = await self._llm_call_with_tools(llm, messages)

        langfuse_context.update_current_observation(name="Agent: Query Reformulator")

        if isinstance(llm_response, str):
            return llm_response.strip()
        return llm_response.content.strip()


query_reformulator_agent = QueryReformulatorAgent()
