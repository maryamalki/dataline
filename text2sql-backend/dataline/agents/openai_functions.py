import json
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.agents import AgentActionMessageLog, AgentFinish, AgentAction
from langchain_core.exceptions import OutputParserException

# from langchain.tools import BaseTool  # , StructuredTool, tool
from langchain.pydantic_v1 import ValidationError, BaseModel


def get_parser(final_tool_name: str, final_base_model: type[BaseModel]):
    def _parse_ai_message(message: BaseMessage) -> AgentAction | AgentFinish:
        """Parse an AI message."""
        if not isinstance(message, AIMessage):
            raise TypeError(f"Expected an AI message got {type(message)}")

        function_call = message.additional_kwargs.get("function_call", {})

        if function_call:
            function_name = function_call["name"]
            try:
                if len(function_call["arguments"].strip()) == 0:
                    # OpenAI returns an empty string for functions containing no args
                    _tool_input = {}
                else:
                    # otherwise it returns a json object
                    _tool_input = json.loads(function_call["arguments"], strict=False)
            except json.JSONDecodeError:
                raise OutputParserException(
                    f"Could not parse tool input: {function_call} because " f"the `arguments` is not valid JSON."
                )

            # HACK HACK HACK:
            # The code that encodes tool input into Open AI uses a special variable
            # name called `__arg1` to handle old style tools that do not expose a
            # schema and expect a single string argument as an input.
            # We unpack the argument here if it exists.
            # Open AI does not support passing in a JSON array as an argument.
            if "__arg1" in _tool_input:
                tool_input = _tool_input["__arg1"]
            else:
                tool_input = _tool_input

            content_msg = f"responded: {message.content}\n" if message.content else "\n"
            log = f"\nInvoking: `{function_name}` with `{tool_input}`\n{content_msg}\n"
            if function_name == final_tool_name:
                try:
                    final_base_model.parse_obj(**tool_input)
                    return AgentFinish(return_values=tool_input, log=str(function_call))
                    # return AgentFinish(return_values={"output": response_obj}, log=str(function_call))
                except ValidationError:
                    return AgentActionMessageLog(
                        tool=function_name,
                        tool_input=tool_input,
                        log=log,
                        message_log=[message],
                    )

            return AgentActionMessageLog(
                tool=function_name,
                tool_input=tool_input,
                log=log,
                message_log=[message],
            )

        return AgentFinish(return_values={"output": message.content}, log=str(message.content))

    return _parse_ai_message
