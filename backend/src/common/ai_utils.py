import os
from typing import Union
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

# add trycatch

def get_llm(**kwargs):
    """Get configured LLM instance"""
    LLM = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        verbose=True,
        **kwargs
    )
    return LLM


def get_llm_response(prompt: Union[str, list], **kwargs) -> str:
    """
    Get response from LLM for a given prompt

    Args:
        prompt: The prompt to send to the LLM. Can be a string or a list
                of message dicts (e.g. [{"role": "system", "content": "..."}])
        **kwargs: Additional arguments to pass to the LLM constructor

    Returns:
        str: The LLM's response text
    """
    llm = get_llm(**kwargs)
    response = llm.invoke(prompt)

    # Extract text content from the response
    if hasattr(response, 'content'):
        return response.content
    elif isinstance(response, str):
        return response
    else:
        return str(response)

