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
from pydantic import Field, model_validator as root_validator
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
    from pydantic import BaseModel, Field, SecretStr, field_validator
    from pydantic import model_validator as root_validator
from langchain_core.runnables import Runnable, RunnableMap, RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain_core.utils import convert_to_secret_str, get_from_dict_or_env
from langchain_core.utils.function_calling import convert_to_openai_tool

logger = logging.getLogger(__name__)




class BaiduQianFanClient(ModelClient):

    def __init__(self,config, **kwargs):
        self.model = config["model"]
        self.top_k = config.get("top_k",4)
        config.pop("model_client_cls",None)
        self.llm_client = BaiduQianfanLLM(**config)

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
            baidu_messages = []
            response = SimpleNamespace()
            response.choices = []
            response.model = self.model

            messages = params["messages"]
            #不支撑system这个角色
            if messages[0]["role"]=="system":
                messages = messages[1:]
            baidu_response = self.llm_client.generate_stream(messages)
            # Send the chat completion request to OpenAI's API and process the response in chunks
            for generation in baidu_response:
                # Decode only the newly generated text, excluding the prompt
                print("baidu_response:", baidu_response)
                print("generation:", generation)
                choice = SimpleNamespace()
                choice.message = SimpleNamespace()
                # if isinstance(llm_result.message, AIMessage):
                choice.message.content = generation["result"]
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
            baidu_messages = []
            messages = params["messages"]
            if messages[0]["role"] == "system":
                messages = messages[1:]
            baidu_response = self.llm_client.generate(messages)
            generation = baidu_response
            # Decode only the newly generated text, excluding the prompt
            print("baidu_response:",baidu_response)
            print("generation:", generation)

            print("generation2:",generation)
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            # if isinstance(llm_result.message, AIMessage):
            choice.message.content = generation["result"]
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


class BaiduQianfanLLM():
    def __init__(self, qianfan_ak="", qianfan_sk="", model="", top_p=0.8, temperature=0.8, penalty_score=1.0, stream=True, request_timeout=60):
        self.qianfan_ak = qianfan_ak
        self.qianfan_sk = qianfan_sk
        self.model = model
        self.top_p = top_p
        self.temperature = temperature
        self.penalty_score = penalty_score
        self.stream = stream
        self.request_timeout = request_timeout
        os.environ["QIANFAN_AK"] = qianfan_ak
        os.environ["QIANFAN_SK"] = qianfan_sk
        os.environ["QIANFAN_AK"] = "iSbdJbzkQRvOLlbWaxBVHKLg"
        os.environ["QIANFAN_SK"] = "0Qa9UEYSXowrnQCH2GQkdL887rfeFuKMe"
        kwargs = {}
        kwargs["model"] = self.model
        kwargs["ak"] = qianfan_ak
        kwargs["sk"] = qianfan_sk
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout
        self.client = qianfan.ChatCompletion()

    def on_llm_new_token(self, token: str):
        # If content is present, print it to the terminal and update response variables、
        content = token
        if content is not None:
            print(content, end="", flush=True)

    def generate_stream(
            self,
            messages: List
    ):
        kwargs = {}
        kwargs["model"]=self.model
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout

        for res in self.client.do(messages, **kwargs):
            if res:
                chunk = res["body"]
                self.on_llm_new_token(res["result"])
                yield chunk


    def generate(
            self,
            messages: List
    ):
        kwargs = {}
        kwargs["model"]=self.model
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout


        res = self.client.do(messages, **kwargs)
        print(res["body"])
        return(res["body"])

