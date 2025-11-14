import asyncio
import os

from app.agents.agent_base import AgentBase
from app.services.watsonx_service import run_sql_query
from langchain.tools.render import render_text_description
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import OpenAIEmbeddings
from langfuse.decorators import langfuse_context, observe
from supabase import create_client, Client
from dotenv import load_dotenv

EMBEDDING_COLUMN = "title_embedding"
TOP_K = 40

load_dotenv()

SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_KEY=os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class BasicAgent(AgentBase):
    def __init__(self):
        super().__init__()
        self._embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    def _get_available_tools(self) -> list[callable]:
        @tool
        async def get_relevant_question_titles(reformulated_user_query: str):
            """
            Pass the user's question to get up to 40 of the most relevant stored questions (id/title pairs).
            To get answers to those question, you must use as well user the get_question_detail_by_id tool with the ids of the questions you find interesting.
            This tool does not provide answers, only questions.
            """
            # Compute query embedding asynchronously
            user_embedding = await asyncio.to_thread(
                self._embeddings.embed_query, reformulated_user_query
            )

            response = supabase.rpc(
                    "match_documents",
                    {
                        "query_embedding": user_embedding,
                        "match_count": 40,
                    },
            ).execute()

            if not response.data:
                return [["id", "question"]]  # empty table fallback

            matrix = [["id", "question"]]
            for row in response.data:
                matrix.append([row["id"], row["Title"]])
            return matrix

        @tool
        async def get_question_detail_by_id(question_id: str):
            """
            Pass a question's id to get more details and an answer.
            You can fetch question ids using the tool get_relevant_question_titles.
            This tool provides answers.
            """
            return await run_sql_query(
                f"SELECT Title, Content FROM supa_pg_db_catalog.public.ai_data WHERE id = CAST('{question_id}' AS uuid)"
            )

        @tool
        async def web_search(query: str):
            """
            Perform a web search to get up-to-date, high-quality search results.
            Useful for finding recent information not in your database.
            You must use sources from the Pole Universitaire Leonard de Vinci website, or the esilv.fr website, or the emlv.fr website.
            """
            results = await asyncio.to_thread(TavilySearchResults(max_results=5).run, query)
            return results

        return [get_relevant_question_titles, get_question_detail_by_id, web_search]

    @observe(as_type="generation")
    async def send_message(self, user_message: str) -> str:
        llm = await self._create_openai_llm()
        messages = []

        tool_descriptions = render_text_description(self.AVAILABLE_TOOLS)

        messages.append(
            SystemMessage(
                content=f"""You are an agentic AI chatbot. Your job is to answer questions about the "Pole Universitaire
                    Leonard de Vinci." Use the tools at your disposal to fetch factual answers to the question of the user.
                    Fetch the list of questions you have answers to, then you can get more informations and factual
                    answers to one, or more. This will help you answer the user correctly.

                    You have access to the following tools to help users:

                    {tool_descriptions}

                    Use these tools when they become helpful to provide better answers to the user.
                    Always be helpful and friendly.
                    Always be factual, if you don't have the answer to a user's question, tell him to contact the "scolarite service" at scolarite@esilv.com
                    You must always answer in the language of the user.
                    You must answer using the markdown format to structure your answers.
                    If a user asks multiple answers, add titles to the markdown answer, to make everything neat.
                    You must call both get_relevant_question_titles and get_question_detail_by_id (eventually more than once)
                    to get factual answers to your questions.
                    """
                    # You must call get_relevant_question_titles twice:
                    # First time by reformulating the user's query in french, second time reformulating in english.
                    # Then chose the question(s) you find most interesting to get factual answers from, and call the get_question_detail_by_id
                    # tool to have the answers of your question, passing the chosen question(s) id(s).
            )
        )

        messages.append(HumanMessage(content=user_message))

        llm_response = await self._llm_call_with_tools(llm, messages)

        langfuse_context.update_current_observation(name="Method: POST message")
        langfuse_context.update_current_trace(
            name="Chat", input=user_message, user_id="Random User", session_id="Random Thread"
        )

        if isinstance(llm_response, str):
            langfuse_context.update_current_trace(output=llm_response)
            return llm_response
        else:
            langfuse_context.update_current_trace(output=llm_response.content)
            return llm_response.content


basic_agent = BasicAgent()
