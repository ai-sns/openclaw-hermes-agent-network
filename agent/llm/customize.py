from __future__ import annotations

from types import SimpleNamespace
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
from langchain_core.pydantic_v1 import Field, root_validator
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
from langchain_core.pydantic_v1 import BaseModel, Field, SecretStr, root_validator
from langchain_core.runnables import Runnable, RunnableMap, RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain_core.utils import convert_to_secret_str, get_from_dict_or_env
from langchain_core.utils.function_calling import convert_to_openai_tool

logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
import json
import os

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")
from globals import global_plugin_list


class CustomizeClient(ModelClient):

    def __init__(self, config, **kwargs):
        self.model = config["model"]
        self.top_k = config.get("top_k", 4)
        plugin_name = config.get("plugin_name", None)
        self.llm_client = self.get_llm_client(plugin_name)

    def get_llm_client(self, plugin_name):
        plugin = global_plugin_list[plugin_name]
        llm_client = plugin.get_model()
        return llm_client

    def parse_api_key(self, key):
        try:
            self.api_key, self.api_secret, self.app_id = key.split("&")
        except Exception as e:
            raise Exception("Invalid Spark API Key")

    def create(self, params):
        print("in customize modelclient")
        iostream = IOStream.get_default()
        if params.get("stream", False) and "messages" in params:
            # Set the terminal text color to green
            # response_contents = [""] * params.get("n", 1)
            response_contents = []
            completion_tokens = 0
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
            llm_response = self.llm_client.generate_stream(messages)
            # Send the chat completion request to OpenAI's API and process the response in chunks
            index = -1
            all_content = ""
            for generation in llm_response:
                # Decode only the newly generated text, excluding the prompt
                print("llm_response:", llm_response)
                print("generation:", generation)
                content = generation
                iostream.print(content, end="", flush=True)
                all_content += content
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            # if isinstance(llm_result.message, AIMessage):
            choice.message.content = all_content
            choice.message.function_call = None


            # elif isinstance(llm_result.message, FunctionMessage):
            #     choice.message.content = llm_result.message.content
            #     choice.message.function_call = llm_result.message.content

            response.choices.append(choice)

            #     if content is not None:
            #         iostream.print(content, end="", flush=True)
            #         response_contents.append("")
            #         response_contents[choice.index] += content
            #         completion_tokens += 1
            #     else:
            #         # iostream.print()
            #         pass
            #
            # # Reset the terminal text color
            # print("\033[0m\n")
            #
            # for i in range(len(response_contents)):
            #     if response_contents[i] == "":
            #         stop_reason = "stop"
            #     else:
            #         stop_reason = "stop"
            #     if OPENAIVERSION >= "1.5":  # pragma: no cover
            #         # OpenAI versions 1.5.0 and above
            #         choice = Choice(
            #             index=i,
            #             # finish_reason="finish_reasons[i]",
            #             finish_reason=stop_reason,
            #             message=ChatCompletionMessage(
            #                 role="assistant",
            #                 content=response_contents[i],
            #                 function_call=full_function_call,
            #                 tool_calls=full_tool_calls,
            #             ),
            #             logprobs=None,
            #         )
            #     else:
            #         # OpenAI versions below 1.5.0
            #         choice = Choice(  # type: ignore [call-arg]
            #             index=i,
            #             # finish_reason="finish_reasons[i]",
            #             finish_reason=stop_reason,
            #             message=ChatCompletionMessage(
            #                 role="assistant",
            #                 content=response_contents[i],
            #                 function_call=full_function_call,
            #                 tool_calls=full_tool_calls,
            #             ),
            #         )
            #
            #     response.choices.append(choice)
            print("got the response:",response)
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
            llm_response = self.llm_client.generate(messages)
            generation = llm_response
            # Decode only the newly generated text, excluding the prompt
            print("llm_response:", llm_response)
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
