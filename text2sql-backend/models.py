from typing import Literal, Union

from pydantic.dataclasses import dataclass


@dataclass
class Result:
    type: Union[Literal["sql"], Literal["code"]]
    content: str


@dataclass
class MessageWithResults:
    content: str
    role: str
    results: list[Result]
    message_id: int = None


@dataclass
class Conversation:
    conversation_id: str
    session_id: str
    name: str


class ConversationWithMessagesWithResults(Conversation):
    messages: list[MessageWithResults]
