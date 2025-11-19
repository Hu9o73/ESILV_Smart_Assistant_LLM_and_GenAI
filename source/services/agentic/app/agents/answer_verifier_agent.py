import json

from app.agents.agent_base import AgentBase
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse.decorators import langfuse_context, observe


class AnswerVerifierAgent(AgentBase):
    def _get_available_tools(self) -> list[callable]:
        return []

    @observe(as_type="generation")
    async def send_message(
        self,
        original_query: str,
        reformulated_query: str,
        proposed_answer: str,
    ) -> dict:
        llm = await self._create_openai_llm()
        messages = [
            SystemMessage(
                content=(
                    "You are the answer verifier agent for the Pole Universitaire Leonard de Vinci (ESILV, EMLV, IIM). "
                    "Critically inspect proposed answers for accuracy, completeness, tone, and alignment with both the "
                    "original user intent and the requirement that all content focus on the Pole and its three schools. "
                    "Approve the answer only if it is fully aligned with the question, grounded in cited evidence related "
                    "to the campus, and follows the user's language. Otherwise, request a revision."
                    '\nRespond strictly in JSON with the following schema: '
                    '{"status": "approved|revise", "final_answer": "string", "feedback": "string describing issues"}. '
                    "When approving, you may lightly edit the final_answer for clarity."
                )
            ),
            HumanMessage(
                content=(
                    f"Original question:\n{original_query}\n\n"
                    f"Reformulated query:\n{reformulated_query}\n\n"
                    f"Proposed answer (markdown allowed):\n{proposed_answer}\n\n"
                    "Return the JSON verdict now."
                )
            ),
        ]

        llm_response = await self._llm_call_with_tools(llm, messages)
        langfuse_context.update_current_observation(name="Agent: Answer Verificator")

        if isinstance(llm_response, str):
            content = llm_response
        else:
            content = llm_response.content

        try:
            verdict = json.loads(content)
        except json.JSONDecodeError:
            verdict = {
                "status": "revise",
                "final_answer": "",
                "feedback": content,
            }

        return verdict


answer_verifier_agent = AnswerVerifierAgent()
