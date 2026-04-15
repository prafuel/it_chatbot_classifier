from app.llm import get_llm
from app.prompt import QUERY_VALIDATOR_PROMPT


def validate_query(query: str, chat_history: list) -> str:
    llm = get_llm()
    response = llm.invoke(QUERY_VALIDATOR_PROMPT.format(chat_history=chat_history, query=query))
    return response.content.strip()