import asyncio

from app.agents.agent_base import AgentBase
from app.database.client import get_db
from langchain.tools.render import render_text_description
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langfuse.decorators import langfuse_context, observe


class DocumentalistAgent(AgentBase):
    def __init__(self):
        super().__init__()
        self._embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    def _get_available_tools(self) -> list[callable]:
        @tool
        async def get_relevant_question_titles(reformulated_user_query: str):
            """
            Fetch up to 40 relevant stored questions (id/title pairs) based on the reformulated query.
            This only provides metadata. Use get_question_detail_by_id to retrieve full answers.
            """
            supabase = get_db()
            user_embedding = await asyncio.to_thread(
                self._embeddings.embed_query,
                reformulated_user_query,
            )

            response = (
                supabase.rpc(
                    "match_documents",
                    {
                        "query_embedding": user_embedding,
                        "match_count": 40,
                    },
                ).execute()
            )

            if not response.data:
                return [["id", "question"]]

            matrix = [["id", "question"]]
            for row in response.data:
                matrix.append([row["id"], row["Title"]])
            return matrix

        @tool
        async def get_question_detail_by_id(question_id: str):
            """
            Retrieve the full question and answer content given a question id.
            """
            supabase = get_db()
            response = (
                supabase.table("ai_data")
                .select("Title, Content")
                .eq("id", question_id)
                .execute()
            )

            if not response.data:
                return [["Title", "Content"]]

            matrix = [["Title", "Content"]]
            for row in response.data:
                matrix.append([row["Title"], row["Content"]])

            return matrix

        return [get_relevant_question_titles, get_question_detail_by_id]

    @observe(as_type="generation")
    async def send_message(self, reformulated_query: str) -> str:
        llm = await self._create_openai_llm()
        tool_descriptions = render_text_description(self.AVAILABLE_TOOLS)
        messages = [
            SystemMessage(
                content=(
                    "You are the documentalist agent for the Pole Universitaire Leonard de Vinci in Paris La Defense, "
                    "home to ESILV, EMLV, and IIM. Use the provided Supabase tools to discover the most relevant stored "
                    "questions about this campus only and extract their factual answers. Combine findings into a concise "
                    "research note that downstream agents can use. Always call get_relevant_question_titles before any "
                    "detail lookup. Summaries must stay factual, cite question ids when referencing, stay in the user's "
                    "language, and exclude information unrelated to the Pole."
                    f"\n\nTools:\n{tool_descriptions}"
                )
            ),
            HumanMessage(
                content=(
                    "Research the following request using the question database and provide the most helpful factual "
                    "notes:\n"
                    f"{reformulated_query}"
                )
            ),
        ]

        llm_response = await self._llm_call_with_tools(llm, messages)
        langfuse_context.update_current_observation(name="Agent: Documentalist")

        if isinstance(llm_response, str):
            return llm_response
        return llm_response.content


documentalist_agent = DocumentalistAgent()
