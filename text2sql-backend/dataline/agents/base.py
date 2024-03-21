from typing import Optional
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.pydantic_v1 import BaseModel, Field, SecretStr
from langchain.tools import BaseTool  # , StructuredTool, tool
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.runnables.config import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy.engine import Engine

from dataline.agents.openai_functions import get_parser
from dataline.agents.prefix import custom_prefix


class Response(BaseModel):
    """Final response to the question being asked"""

    answer: str = Field(description="The final answer to respond to the user")
    sql_query: Optional[str] = Field(description="sql query used to get the final answer")


class FinalResponseValidationTool(BaseTool):
    name = "prepare_final_response"
    description = "always use this before sending the final answer"
    args_schema: type[BaseModel] = Response

    def handle_validation_error(self, e):
        return f"Got a validation error: {e.json()}"

    def _run(
        self, answer: str, sql_query: str | None, run_manager: CallbackManagerForToolRun | None = None
    ) -> Response:
        """Use the tool."""
        return Response.parse_obj({answer: answer, sql_query: sql_query})


final_response_validation_tool = FinalResponseValidationTool()  # no, description is not needed.


class SQLAgent:
    def __init__(self, openai_api_key: str, engine: Engine, model="gpt-3.5-turbo"):
        db = SQLDatabase(engine=engine)
        llm = ChatOpenAI(temperature=0.1, openai_api_key=SecretStr(openai_api_key), model=model)
        toolkit = SQLDatabaseToolkit(llm=llm, db=db)
        llm_tools = [convert_to_openai_function(t) for t in [*toolkit.get_tools(), final_response_validation_tool]]
        llm_with_tools = llm.bind_functions(llm_tools)
        custom_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", custom_prefix.format(dialect=toolkit.dialect, top_k=10)),
                MessagesPlaceholder("chat_history", optional=True),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        self.agent = (
            {
                "input": lambda x: x["input"],
                # Format agent scratchpad from intermediate steps
                "agent_scratchpad": lambda x: format_to_openai_function_messages(x["intermediate_steps"]),
            }
            | custom_prompt
            | llm_with_tools
            | get_parser(final_response_validation_tool.name, final_response_validation_tool.args_schema)
        )
        self.agent_executor = AgentExecutor(tools=toolkit.get_tools(), agent=self.agent, return_intermediate_steps=True)

    def invoke(self, input_dict: dict, config: RunnableConfig | None = None, **kwargs):
        return self.agent_executor.invoke(input_dict, config, **kwargs)
