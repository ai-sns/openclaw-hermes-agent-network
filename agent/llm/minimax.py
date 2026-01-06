from __future__ import annotations

from types import SimpleNamespace
from typing import Optional, List, Dict, Any

import qianfan
from autogen import ModelClient

from sparkai.core.callbacks import BaseCallbackHandler
from sparkai.core.messages import ChatMessage, AIMessage, FunctionMessage
from sparkai.llm.llm import ChatSparkLLM

import inspect
import json
from typing import Any, Dict, List, Union

import os
import requests
import json
from openai.types.chat.chat_completion import ChatCompletionMessage
from typing_extensions import Annotated
from typing_extensions import Annotated
from autogen.oai.client import OpenAIWrapper
import autogen
from autogen import AssistantAgent, UserProxyAgent

from openai import OpenAI

import inspect
import logging
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union

from flaml.automl.logger import logger_formatter
from pydantic import BaseModel

from autogen.cache import Cache
from autogen.io.base import IOStream
from autogen.logger.logger_utils import get_current_ts
from autogen.oai.openai_utils import OAI_PRICE1K, get_key, is_valid_api_key
from autogen.runtime_logging import log_chat_completion, log_new_client, log_new_wrapper, logging_enabled
from autogen.token_count_utils import count_token
from autogen import ModelClient

TOOL_ENABLED = False
try:
    import openai
except ImportError:
    ERROR: Optional[ImportError] = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")
    OpenAI = object
    AzureOpenAI = object
else:
    # raises exception if openai>=1 is installed and something is wrong with imports
    from openai import APIError, APITimeoutError, AzureOpenAI, OpenAI
    from openai import __version__ as OPENAIVERSION
    from openai.resources import Completions
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice  # type: ignore [attr-defined]
    from openai.types.chat.chat_completion_chunk import (
        ChoiceDeltaFunctionCall,
        ChoiceDeltaToolCall,
        ChoiceDeltaToolCallFunction,
    )
    from openai.types.completion import Completion
    from openai.types.completion_usage import CompletionUsage

    if openai.__version__ >= "1.1.0":
        TOOL_ENABLED = True
    ERROR = None

try:
    from autogen.oai.gemini import GeminiClient
    from autogen.oai.client import OpenAIWrapper

    gemini_import_exception: Optional[ImportError] = None
except ImportError as e:
    gemini_import_exception = e

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)

LEGACY_DEFAULT_CACHE_SEED = 41
LEGACY_CACHE_DIR = ".cache"
OPEN_API_BASE_URL_PREFIX = "https://api.openai.com"

import logging
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Optional,
)

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
try:
    from langchain_core.pydantic_v1 import Field, root_validator
except ImportError:
    from pydantic import Field
    from pydantic import model_validator as root_validator
from langchain_core.utils import convert_to_secret_str, get_from_dict_or_env

logger = logging.getLogger(__name__)

import logging
from operator import itemgetter
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.output_parsers.base import OutputParserLike
from langchain_core.output_parsers.openai_tools import (
    JsonOutputKeyToolsParser,
    PydanticToolsParser,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
try:
    from langchain_core.pydantic_v1 import BaseModel, Field, SecretStr, root_validator
except ImportError:
    from pydantic import BaseModel, Field, SecretStr
    from pydantic import model_validator as root_validator
from langchain_core.runnables import Runnable, RunnableMap, RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain_core.utils import convert_to_secret_str, get_from_dict_or_env
from langchain_core.utils.function_calling import convert_to_openai_tool

logger = logging.getLogger(__name__)


class MiniMaxClient(ModelClient):

    def __init__(self, config, **kwargs):
        self.model = config["model"]
        self.top_k = config.get("top_k", 4)
        self.api_key = config.get("api_key", "")
        config.pop("model_client_cls", None)
        self.llm_client = MiniMaxLLM(**config)

    def parse_api_key(self, key):
        try:
            self.api_key, self.api_secret, self.app_id = key.split("&")
        except Exception as e:
            raise Exception("Invalid Spark API Key")

    def create(self, params):
        if params.get("stream", False) and "messages" in params:
            # Set the terminal text color to green
            print("\033[32m", end="")

            # Prepare for potential function call
            full_function_call: Optional[Dict[str, Any]] = None
            full_tool_calls: Optional[List[Optional[Dict[str, Any]]]] = None
            minimax_messages = []
            response = SimpleNamespace()
            response.choices = []
            response.model = self.model

            messages = params["messages"]
            if messages[0]["role"] == "system":
                messages = messages[1:]
            minimax_response = self.llm_client.generate_stream(messages)
            # Send the chat completion request to OpenAI's API and process the response in chunks
            for generation in minimax_response:
                # Decode only the newly generated text, excluding the prompt
                print("minimax_response:", minimax_response)
                print("generation:", generation)
                choice = SimpleNamespace()
                choice.message = SimpleNamespace()
                # if isinstance(llm_result.message, AIMessage):
                choice.message.content = generation
                choice.message.function_call = None
                # elif isinstance(llm_result.message, FunctionMessage):
                #     choice.message.content = llm_result.message.content
                #     choice.message.function_call = llm_result.message.content

                response.choices.append(choice)

            # Reset the terminal text color
            print("\033[0m\n")

            return response
        else:
            num_of_responses = self.top_k

            # can create my own data response class
            # here using SimpleNamespace for simplicity
            # as long as it adheres to the ClientResponseProtocol

            response = SimpleNamespace()
            response.choices = []
            response.model = self.model
            minimax_messages = []
            messages = params["messages"]
            if messages[0]["role"] == "system":
                messages = messages[1:]
            minimax_response = self.llm_client.generate(messages)
            generation = minimax_response
            # Decode only the newly generated text, excluding the prompt
            print("minimax_response:", minimax_response)
            print("generation:", generation)

            print("generation2:", generation)
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            # if isinstance(llm_result.message, AIMessage):
            choice.message.content = generation
            choice.message.function_call = None
            # elif isinstance(llm_result.message, FunctionMessage):
            #     choice.message.content = llm_result.message.content
            #     choice.message.function_call = llm_result.message.content

            response.choices.append(choice)

            return response

    def message_retrieval(self, response):
        """Retrieve the messages from the response."""
        choices = response.choices
        return [choice.message.content for choice in choices]

    def cost(self, response) -> float:
        """Calculate the cost of the response."""
        response.cost = 0
        return 0

    @staticmethod
    def get_usage(response):
        # returns a dict of prompt_tokens, completion_tokens, total_tokens, cost, model
        # if usage needs to be tracked, else None
        return {}


class MiniMaxLLM():
    def __init__(self, api_key="",model="", top_p=0.8, temperature=0.8, stream=True):
        self.url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
        self.api_key = api_key
        self.model = model
        self.top_p = top_p
        self.temperature = temperature
        self.stream = stream

    def on_llm_new_token(self, token: str):
        # If content is present, print it to the terminal and update response variables、
        content = token
        if content is not None:
            print(content, end="", flush=True)

    def generate_stream(
            self,
            messages: List
    ):

        url = self.url
        api_key = self.api_key
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 1000,
            "temperature": self.temperature,
            "top_p": self.top_p
        })
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload, stream=True)  # request也要指定stream=True
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: ") and decoded_line.strip() != "data: [DONE]":
                    try:
                        chunk = json.loads(decoded_line[6:])
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            chunk_message = chunk['choices'][0].get('delta', {}).get('content', '')
                            if chunk_message:
                                print("chunk_message:", chunk_message)
                                yield chunk_message
                    except json.JSONDecodeError:
                        continue

    def generate(
            self,
            messages: List
    ):
        url = self.url
        api_key = self.api_key
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": 1000,
            "temperature": self.temperature,
            "top_p": self.top_p
        })
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload, stream=False)
        print(response.text)
        chunk = json.loads(response.text)
        print(chunk['choices'][0].get('message', {}).get('content', ''))
        content = chunk['choices'][0].get('message', {}).get('content', '')
        return content
