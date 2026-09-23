from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from . import config


def get_chat_model() -> BaseChatModel:
    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
        temperature=0,
    )
