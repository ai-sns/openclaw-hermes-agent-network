from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.apps.sns.map_task_manager import MapTaskManager
from backend.apps.sns.js_task_manager import JsTaskManager
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.modules.agent.agent_manager import agent_manager
from backend.shared.websocket_manager import manager as websocket_manager

from backend.database.repositories.system_repository import PluginMngRepository, FunctionMngRepository, McpMngRepository, SkillMngRepository
from backend.modules.agent.tool_converter import ToolConverter

# *********
import os
import math
# Mainly used for sending attachments
import asyncio
import zipfile
import shutil
import time

import logging

import re

log = logging.getLogger(__name__)
from db.DBFactory import (query_AgentCfg, add_AIChatMessages, get_prompt_by_title, query_function_mng,
                          add_function_mng, add_map_visit, get_key_value,
                          update_map_trade, add_map_trade, query_single_map_trade, update_AiChatCfg_by_user_id, update_AiChatCfg_map, query_AiChatCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_AiChatCfg_map_setting)
from util import (generate_random_id, add_memory_list)
from i18n import lt
from enum import Enum
from typing import List, Dict, Optional
import json
import logging
import requests
import geopy.distance
from geopy.distance import distance
from geopy.point import Point
from geographiclib.geodesic import Geodesic
import random

from backend.shared.utils import robust_json_loads

logger = logging.getLogger(__name__)


class ToolsMixin:

    _WEB_SERVICE_TIMEOUT = (3, 15)
    _WEB_SERVICE_MAX_RETRIES = 3
    _WEB_SERVICE_RETRY_BACKOFF = (0.5, 1.0, 2.0)

    def _get_ai_sns_server_base(self):
        try:
            from db.DBFactory import query_SystemCfg
            cfg = query_SystemCfg(is_delete=False)
            v = getattr(cfg, 'ai_sns_server', None)
            v = (v or '').strip()
            return v.rstrip('/') if v else ''
        except Exception:
            return ''

    def use_service(self, action_str, instrunction):
        asyncio.create_task(
            self.ask_agent_to_use_service(
                action_str,
                human_objective_to_achieve=instrunction,
            )
        )

    def get_service_list(self):
        url = f"{self._get_ai_sns_server_base()}/api/get_service_list/"

        pos = self.aichatcfg_record.current_position

        try:
            lng_val = float(pos[0])
            lat_val = float(pos[1])
            pos_key = f"{round(lng_val, 6)},{round(lat_val, 6)}"
        except Exception:
            pos_key = ""

        try:
            cached_key = getattr(self, "_cached_service_list_pos_key", None)
            cached_value = getattr(self, "_cached_service_list_value", None)
            if pos_key and cached_key == pos_key and cached_value is not None:
                return cached_value
        except Exception:
            pass

        params = {
            "lng": pos[0],
            "lat": pos[1]
        }
        service_list = self.http_request(url, params)

        if isinstance(service_list, list) and pos_key:
            try:
                setattr(self, "_cached_service_list_pos_key", pos_key)
                setattr(self, "_cached_service_list_value", service_list)
            except Exception:
                pass
        return service_list

    def update_service_list(self):
        url = f"{self._get_ai_sns_server_base()}/api/get_service"
        params = {
            "lng": self.aichatcfg_record.current_position[0],
            "lat": self.aichatcfg_record.current_position[1]
        }
        # people={
        #     "name":"Same",
        #     "position":[121.121,23.4554]
        # }
        service_list = self.http_request(url, params)

        return service_list

    async def ask_agent_to_use_service(self, objective_to_achieve, human_objective_to_achieve=""):
        service_list = json.dumps(self.get_service_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"
        role_prompt = get_prompt_by_title("__ask_agent_use_service__")
        role_prompt = role_prompt.replace("__service_list__", service_list)
        # role_prompt = role_prompt.replace("__objective_to_achieve__", objective_to_achieve)


        question = f"The current objective is: {objective_to_achieve}. Based on the task requirements, select the appropriate services. If no suitable service is available, return an empty list."

        # Memory recall: inject past service usage experience
        try:
            from backend.apps.sns.memory.memory_types import MemoryType
            from backend.apps.sns.memory.memory_config import MemoryConfig
            mm = getattr(self, "memory_manager", None)
            if mm and MemoryConfig.ENABLED:
                memory_section = mm.get_memory_prompt_section(
                    query=objective_to_achieve,
                    memory_types=[MemoryType.EPISODE.value, MemoryType.OBSERVATION.value],
                    max_results=3,
                    max_chars=800,
                )
                if memory_section:
                    question += "\n\n" + memory_section
        except Exception as _mem_err:
            logger.warning("Memory recall failed for service selection: %s", _mem_err)

        self.command_status = "ask_agent_to_use_service"
        await self.ask_agent_and_get_instruction(question, role_prompt)

    def on_ask_agent_to_use_service_return(self, content):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._handle_service_selection_and_call_async(content))
        except RuntimeError:
            asyncio.run(self._handle_service_selection_and_call_async(content))


    def parse_content_to_call_service(self, content):
        try:
            url, method, params = self._parse_service_call_payload(content)
            response = self.call_service(url, method, **params)
            return response
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error processing content: {e}")
            return None

    def _parse_service_call_payload(self, content):
        data = robust_json_loads(content, default=None)
        if not isinstance(data, dict):
            raise ValueError("Invalid service selection payload (not a JSON object)")

        url = data.get("address")
        method = (data.get("method") or "get").lower()
        params = data.get("parameter")
        if params is None:
            params = data.get("Parameter", {})
        if params is None:
            params = {}

        if not isinstance(url, str) or not url.startswith("http"):
            raise ValueError("Invalid 'address' value. Must be a valid URL.")

        if method not in ["get", "post", "put", "delete", "patch"]:
            raise ValueError("Invalid 'method' value. Supported methods: get, post, put, delete, patch")

        if not isinstance(params, dict):
            raise ValueError("Invalid 'parameter' value. Must be a JSON object.")

        return url, method, params

    async def _handle_service_selection_and_call_async(self, content: str):
        url = ""
        method = ""
        params = {}
        try:
            try:
                url, method, params = self._parse_service_call_payload(content)
            except Exception as e:
                msg = f"Invalid service payload: {e}"
                try:
                    self.show_alert_on_map(msg)
                except Exception:
                    pass
                try:
                    self.taskmng.add_process_info_to_list(f"system: {msg}")
                except Exception:
                    pass
                try:
                    self.write_thinking_process_to_pane("Service selection parse failed", msg)
                except Exception:
                    pass
                try:
                    self.show_status_on_map("idle")
                except Exception:
                    pass
                try:
                    if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                        self._maybe_finish_human_command_if_idle(ask_content="")
                    else:
                        asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=""))
                except Exception:
                    pass
                return

            try:
                self.command_status = ""
            except Exception:
                pass

            response_text = await self._call_web_service_with_retry_async(url, method, params)
            if response_text is not None:
                try:
                    self.handle_service_called_result(response_text)
                except Exception as e:
                    msg = f"Service call returned but handling failed: {e}"
                    try:
                        self.show_alert_on_map(msg, is_error=True)
                    except Exception:
                        pass
                    try:
                        self.taskmng.add_process_info_to_list(f"system: {msg}")
                    except Exception:
                        pass
                    try:
                        self.write_thinking_process_to_pane("Service call handling failed", msg)
                    except Exception:
                        pass
                    try:
                        self.show_status_on_map("idle")
                    except Exception:
                        pass
                    try:
                        if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                            self._maybe_finish_human_command_if_idle(ask_content="")
                        else:
                            asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=""))
                    except Exception:
                        pass
                return

            final_msg = f"Web service call failed after retries: {method.upper()} {url}"
            try:
                self.show_alert_on_map(final_msg, is_error=True)
            except Exception:
                pass
            try:
                self.taskmng.add_process_info_to_list(f"system: {final_msg}")
            except Exception:
                pass
            try:
                self.write_thinking_process_to_pane("Web service call failed", final_msg)
            except Exception:
                pass
            try:
                self.show_status_on_map("idle")
            except Exception:
                pass

            try:
                if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                    self._maybe_finish_human_command_if_idle(ask_content="")
                else:
                    asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=""))
            except Exception:
                pass
        except Exception as e:
            msg = f"Unexpected error while handling service selection: {e}"
            try:
                self.show_alert_on_map(msg, is_error=True)
            except Exception:
                pass
            try:
                self.taskmng.add_process_info_to_list(f"system: {msg}")
            except Exception:
                pass
            try:
                self.write_thinking_process_to_pane("Service selection failed", msg)
            except Exception:
                pass
            try:
                self.show_status_on_map("idle")
            except Exception:
                pass
            try:
                if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                    self._maybe_finish_human_command_if_idle(ask_content="")
                else:
                    asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=""))
            except Exception:
                pass

    async def _call_web_service_with_retry_async(self, url: str, method: str, params: dict):
        max_retries = int(getattr(self, "_WEB_SERVICE_MAX_RETRIES", self._WEB_SERVICE_MAX_RETRIES) or 3)
        backoffs = getattr(self, "_WEB_SERVICE_RETRY_BACKOFF", self._WEB_SERVICE_RETRY_BACKOFF) or (0.5, 1.0, 2.0)
        timeout = getattr(self, "_WEB_SERVICE_TIMEOUT", self._WEB_SERVICE_TIMEOUT) or (3, 15)

        try:
            self.show_status_on_map("using-tool")
        except Exception:
            pass

        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                def _do_request():
                    m = (method or "get").lower()
                    if m in ["get", "delete"]:
                        resp = requests.request(m, url, params=params, timeout=timeout)
                    else:
                        resp = requests.request(m, url, json=params, timeout=timeout)
                    resp.raise_for_status()
                    return resp.text

                if hasattr(asyncio, "to_thread"):
                    result = await asyncio.to_thread(_do_request)
                else:
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, _do_request)
                try:
                    self.show_status_on_map("idle")
                except Exception:
                    pass
                return result
            except requests.exceptions.RequestException as e:
                last_err = e
                msg = f"Web service call failed (attempt {attempt}/{max_retries}): {e}"
                try:
                    self.taskmng.add_process_info_to_list(f"system: {msg}")
                except Exception:
                    pass
                try:
                    self.write_thinking_process_to_pane("Web service call failed", msg)
                except Exception:
                    pass
            except Exception as e:
                last_err = e
                msg = f"Web service call error (attempt {attempt}/{max_retries}): {e}"
                try:
                    self.taskmng.add_process_info_to_list(f"system: {msg}")
                except Exception:
                    pass
                try:
                    self.write_thinking_process_to_pane("Web service call error", msg)
                except Exception:
                    pass

            if attempt < max_retries:
                try:
                    backoff = float(backoffs[attempt - 1]) if attempt - 1 < len(backoffs) else float(backoffs[-1])
                except Exception:
                    backoff = 0.5
                await asyncio.sleep(max(0.0, backoff))

        try:
            self.show_status_on_map("idle")
        except Exception:
            pass

        try:
            if last_err is not None:
                logger.warning("Web service call failed after retries: %s %s, last_err=%s", method, url, last_err)
        except Exception:
            pass
        return None

    def call_service(self, url, method, **params):
        try:
            timeout = getattr(self, "_WEB_SERVICE_TIMEOUT", None) or (3, 15)
            if method == "get":
                response = requests.get(url, params=params, timeout=timeout)
            elif method == "post":
                response = requests.post(url, json=params, timeout=timeout)  # Use 'data' for post
            elif method == "put":
                response = requests.put(url, json=params, timeout=timeout)
            elif method == "delete":
                response = requests.delete(url, params=params, timeout=timeout)
            elif method == "patch":
                response = requests.patch(url, json=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            self.handle_service_called_result(response.text)  # Assuming the response is JSON, parse and return it
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error calling service: {e}")
            return None  # Or handle the error as needed, e.g., retry, log, etc.
        except ValueError as e:
            print(f"Error calling service: {e}")
            return None

    def run_configured_tool_text_generation_sync(
        self,
        tool_name: str,
        what_to_do: str,
        *,
        conversation_suffix: str = "configured_tool",
        force_tool_call: bool = False,
    ):
        try:
            return asyncio.create_task(
                self.generate_text_with_configured_tool(
                    tool_name,
                    what_to_do,
                    conversation_suffix=conversation_suffix,
                    force_tool_call=force_tool_call,
                )
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.generate_text_with_configured_tool(
                        tool_name,
                        what_to_do,
                        conversation_suffix=conversation_suffix,
                        force_tool_call=force_tool_call,
                    )
                )
            finally:
                loop.close()

    def ask_agent_to_run_a_tool_sync(self, tool_name: str, what_to_do: str):
        return self.run_configured_tool_text_generation_sync(
            tool_name,
            what_to_do,
            conversation_suffix="configured_tool",
        )

    async def _ask_agent_to_use_configured_tool(self, tool_name: str, what_to_do: str) -> str:
        return await self.generate_text_with_configured_tool(
            tool_name,
            what_to_do,
            conversation_suffix="configured_tool",
        )

    def _load_tool_def_for_agent(self, tool_type: str, tool_id: str, *, mcp_tool_name: str = "") -> Optional[dict]:
        return self.load_openai_tool_def_for_agent(tool_type, tool_id, mcp_tool_name=mcp_tool_name)

    def handle_service_called_result(self, response_text):
        action_result = response_text
        self.action_result = action_result
        self.taskmng.add_process_info_to_list(f"system: Web service called and returned: {action_result}")
        self.write_task_process_to_pane(action_result + "\n\n")
        self.show_alert_on_map(action_result)
        ask_content = ""
        try:
            if bool(getattr(self, "_human_command_inflight", False)) and hasattr(self, "_maybe_finish_human_command_if_idle"):
                self._maybe_finish_human_command_if_idle(ask_content=ask_content)
            else:
                asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=ask_content))
        except Exception:
            pass

    async def generate_text_with_configured_tool(
        self,
        tool_name: str,
        what_to_do: str,
        *,
        conversation_suffix: str = "configured_tool",
        force_tool_call: bool = False,
    ) -> str:
        if not tool_name:
            raise ValueError("tool_name is empty")

        parts = tool_name.split(":")
        if len(parts) < 2:
            raise ValueError(f"invalid tool_name format: {tool_name}")

        tool_type = (parts[0] or "").strip().lower()
        tool_id = (parts[1] or "").strip()
        mcp_tool_name = (parts[2] or "").strip() if len(parts) >= 3 else ""

        if not tool_type or not tool_id:
            raise ValueError(f"invalid tool_name format: {tool_name}")

        if tool_type == "mcp" and not mcp_tool_name:
            raise ValueError(f"invalid mcp tool_name format (expected mcp:mcp_id:tool_name): {tool_name}")

        if tool_type not in {"plugin", "function", "skill", "mcp"}:
            raise ValueError(f"unsupported tool type: {tool_type}")

        tool_def = self.load_openai_tool_def_for_agent(tool_type, tool_id, mcp_tool_name=mcp_tool_name)
        if tool_def is None:
            if tool_type == "mcp":
                raise ValueError(f"tool not found: {tool_type}:{tool_id}:{mcp_tool_name}")
            raise ValueError(f"tool not found: {tool_type}:{tool_id}")

        tool_choice = None
        if force_tool_call:
            tool_fn = tool_def.get("function") if isinstance(tool_def, dict) else None
            tool_fn_name = (tool_fn or {}).get("name") if isinstance(tool_fn, dict) else None
            if isinstance(tool_fn_name, str) and tool_fn_name:
                tool_choice = {"type": "function", "function": {"name": tool_fn_name}}
            else:
                logger.warning("force_tool_call is enabled but tool function name is missing")

        agent = None
        if hasattr(self, "get_agent_for_current_chat"):
            agent = self.get_agent_for_current_chat()
        if agent is None:
            raise RuntimeError("agent not configured for current user")

        original_db_tools = getattr(agent, "db_tools", None)
        original_tools = getattr(agent, "tools", None)
        original_tools_loaded = getattr(agent, "tools_loaded", None)

        try:
            agent.db_tools = [tool_def]
            agent.tools = []
            agent.tools_loaded = True

            prompt = (
                "你现在只能使用我提供给你的这一个工具来完成内容生成。\n"
                "你可以选择调用该工具，也可以选择不调用。\n"
                "无论是否调用工具，都必须输出最终文本内容，不要输出多余解释。\n\n"
                f"上下文如下：\n{what_to_do}"
            )

            reply = await self.chat_with_agent(
                prompt,
                conversation_suffix=conversation_suffix,
                use_tools=True,
                use_memory=False,
                use_knowledge_base=False,
                tool_choice=tool_choice,
                agent=agent,
            )

            reply = (reply or "").strip()
            if reply:
                return reply
            return "(No content generated)"
        finally:
            agent.db_tools = original_db_tools
            agent.tools = original_tools
            agent.tools_loaded = original_tools_loaded

    def load_openai_tool_def_for_agent(self, tool_type: str, tool_id: str, *, mcp_tool_name: str = "") -> Optional[dict]:
        try:
            if tool_type == "plugin":
                repo = PluginMngRepository()
                obj = repo.get_one(plugin_id=tool_id)
                if not obj:
                    return None
                tool_dict = {
                    "tool_type": "plugin",
                    "plugin_id": getattr(obj, "plugin_id", tool_id),
                    "name": getattr(obj, "name", ""),
                    "description": getattr(obj, "description", ""),
                    "instruction": getattr(obj, "instruction", ""),
                    "parameter": getattr(obj, "parameter", "{}"),
                }
                return ToolConverter.plugin_to_openai(tool_dict)

            if tool_type == "function":
                repo = FunctionMngRepository()
                obj = repo.get_one(function_id=tool_id)
                if not obj:
                    return None
                tool_dict = {
                    "tool_type": "function",
                    "function_id": getattr(obj, "function_id", tool_id),
                    "name": getattr(obj, "name", ""),
                    "description": getattr(obj, "description", ""),
                    "instruction": getattr(obj, "instruction", ""),
                    "parameter": getattr(obj, "parameter", "{}"),
                }
                return ToolConverter.function_to_openai(tool_dict)

            if tool_type == "skill":
                repo = SkillMngRepository()
                obj = repo.get_one(skill_id=tool_id)
                if not obj:
                    return None
                tool_dict = {
                    "tool_type": "skill",
                    "skill_id": getattr(obj, "skill_id", tool_id),
                    "name": getattr(obj, "name", ""),
                    "description": getattr(obj, "description", ""),
                    "instruction": getattr(obj, "instruction", ""),
                    "parameter": getattr(obj, "parameter", "{}"),
                }
                return ToolConverter.skill_to_openai(tool_dict)

            if tool_type == "mcp":
                if not mcp_tool_name:
                    return None

                repo = McpMngRepository()
                obj = repo.get_one(mcp_id=tool_id)
                if not obj:
                    return None

                mcp_dict = {
                    "tool_type": "mcp",
                    "mcp_id": getattr(obj, "mcp_id", tool_id),
                    "name": getattr(obj, "name", ""),
                    "description": getattr(obj, "description", ""),
                }

                tool_schema = None
                parameter = getattr(obj, "parameter", None)
                if parameter:
                    try:
                        param_data = json.loads(parameter) if isinstance(parameter, str) else parameter
                        if isinstance(param_data, dict):
                            tools_list = param_data.get("tools")
                            if isinstance(tools_list, list):
                                for t in tools_list:
                                    if not isinstance(t, dict):
                                        continue
                                    if (t.get("name") or "").strip() == mcp_tool_name:
                                        tool_schema = t
                                        break
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse MCP parameters: {parse_error}")

                input_schema = None
                if isinstance(tool_schema, dict):
                    input_schema = tool_schema.get("inputSchema") or tool_schema.get("parameters")

                tool_dict = {
                    "name": mcp_tool_name,
                    "description": (tool_schema or {}).get("description") if isinstance(tool_schema, dict) else f"Execute MCP tool '{mcp_tool_name}'",
                    "inputSchema": input_schema
                    if isinstance(input_schema, dict)
                    else {
                        "type": "object",
                        "properties": {},
                    },
                }

                return ToolConverter.mcp_to_openai(mcp_dict, tool_dict)

        except Exception as e:
            logger.error(f"load tool def failed: {tool_type}:{tool_id}: {e}", exc_info=True)
            return None

        return None
