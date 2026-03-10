import json
import asyncio
from db.DBFactory import query_single_map_task, update_map_task
from db.DBFactory import get_prompt_by_title
from i18n import lt
from typing import Dict, Any, Optional
from util import generate_random_id
import logging
from backend.shared.utils import robust_json_loads

logger = logging.getLogger(__name__)


class MapTaskManager:
    def __init__(self, parent):
        # def __init__(self, parent:MessageBox):
        # Initialize a dict and several lists
        self.parent = parent
        self.js_task_manager = None
        self.message_dict = {}
        self.specified_context_message_list = []
        self.specify_context_message_flag = False
        self._process_lock = asyncio.Lock()
        self.kwargs = {}
        self.init_flag = False
        self.last_param = {}
        self.current_activity_objective = ""
        self.current_objective = ""
        self.current_task_record = None
        self.main_task = ""
        self.sub_task_list = []
        self.current_sub_task = None
        self.current_sub_task_index = 0
        self.process_info_list = []
        self.process_list = []
        self.current_process = None

        self.current_situation = ""

        self._process_info_compacting = False
        self.reviewing_current_process = False
        self.reviewing_task = False

        self._process_history_flush_task = None

        self._pick_people_format_retry = {
            "communication": 0,
            "sell": 0,
            "buy": 0,
        }

        self.init_task_mng()

    @staticmethod
    def _validate_people_selection_result(people_dict: Any) -> (bool, list):
        required_keys = ["nation_id", "account", "message", "nick_name"]
        if not isinstance(people_dict, dict):
            return False, required_keys

        missing = []
        for k in required_keys:
            v = people_dict.get(k, None)
            if not isinstance(v, str) or not v.strip():
                missing.append(k)
        return len(missing) == 0, missing

    def _retry_pick_people_selection(self, *, talk_type: str, raw_result: str, missing_keys: list) -> bool:
        retry_count = int(self._pick_people_format_retry.get(talk_type, 0) or 0)
        if retry_count >= 3:
            logger.warning(
                f"Invalid people selection result, reached max retries (talk_type={talk_type}, missing={missing_keys})."
            )
            self._pick_people_format_retry[talk_type] = 0
            asyncio.create_task(self.parent.taskmng.process_task(event="agent_pick_people_list_fail"))
            return False

        title_map = {
            "communication": (
                "ask_agent_start_to_talk_to_a_people",
                "__start_to_talk_to_a_people__",
                "__start_to_talk_to_a_people_content__",
            ),
            "sell": (
                "ask_agent_start_to_sell_to_a_people",
                "__start_to_sell_to_a_people__",
                "__start_to_sell_to_a_people_content__",
            ),
            "buy": (
                "ask_agent_start_to_buy_from_a_people",
                "__start_to_buy_from_a_people__",
                "__start_to_buy_from_a_people_content__",
            ),
        }
        command_status, role_title, content_title = title_map.get(talk_type, ("", "", ""))
        if not command_status:
            self._pick_people_format_retry[talk_type] = 0
            asyncio.create_task(self.parent.taskmng.process_task(event="agent_pick_people_list_fail"))
            return False

        self._pick_people_format_retry[talk_type] = retry_count + 1

        objective_to_achieve = (getattr(self.parent, "_pending_talk_objective", None) or "").strip()
        people_list = []
        try:
            people_list = self.parent._get_filtered_people_list_for_talk_type(talk_type) or []
        except Exception:
            people_list = []

        provided_profile_list = json.dumps(people_list, indent=4, ensure_ascii=False)
        role_prompt = get_prompt_by_title(role_title) or ""
        content_prompt = (get_prompt_by_title(content_title) or "")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        strict_instruction = (
            "Your previous output was invalid. Output ONLY one JSON object (no markdown, no extra text) "
            "with EXACT keys: nation_id, account, nick_name, message. All values must be non-empty strings. "
            f"Missing/invalid keys: {missing_keys}. Previous raw output: {str(raw_result)[:300]}"
        )
        content_prompt = f"{content_prompt}\n\n{strict_instruction}"

        logger.warning(
            f"Invalid people selection result, retrying (talk_type={talk_type}, retry={retry_count + 1}/3, missing={missing_keys})."
        )
        self._instruction_invalid_count += 1
        self._update_iq_point_from_counters()

        self.set_command_status(command_status)
        asyncio.create_task(self.parent.ask_agent_and_get_instruction(content_prompt, role_prompt))
        return True

    def init_task_mng(self):
        self.message_dict.clear()
        self.specified_context_message_list.clear()
        self.specify_context_message_flag = False
        self.kwargs.clear()

        self.current_activity_objective = ""
        self.current_objective = ""
        self.current_task_record = None
        self.main_task = ""
        self.sub_task_list = []
        self.current_sub_task = None
        self.current_sub_task_index = 0
        self.process_info_list = []
        self.process_list = []
        self.current_process = None
        self.current_situation = ""

        self._process_info_compacting = False

        self.js_task_manager = self.parent.taskmng_js
        self.current_task_record = query_single_map_task(status=1)
        if self.current_task_record:
            self.main_task = self.current_task_record.detail

        self.current_objective = ""
        self.init_flag = True

    def re_init(self):
        # Clear dict/list and reset flags
        self.message_dict.clear()
        self.specified_context_message_list.clear()
        self.specify_context_message_flag = False

    def get_task_summary(self):
        # Join process info list into a string with newlines
        # Add sequence numbers for each item in the process info list
        process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.process_info_list))
        command_status = self.parent.command_status
        result = f"""### Task Description
#### **Background**
I am participating in a virtual social game based on Google Maps. Players role-play characters to explore, socialize, and complete tasks on a virtual map.

---

#### **Task Execution Process Log**
{process_info_list_str}

---
        """
        return result

    def get_current_objective(self):
        objective = self.current_objective
        return objective

    def get_current_activity_objective(self):
        objective = self.current_activity_objective
        return objective

    def add_process(self, **kwargs) -> str:
        """Add a new process to process_list and update current_process."""
        new_process = {
            "id": generate_random_id(),
            "current_place": kwargs.get("current_place", ""),
            "current_position": kwargs.get("current_position", []),
            "tool_used_count": kwargs.get("tool_used_count", 0),
            "people_communicated_count": kwargs.get("people_communicated_count", 0),
            "people_communicated_list": kwargs.get("people_communicated_list", []),
            "rounds_current_person": kwargs.get("rounds_current_person", 0),
            "ability_used_list": kwargs.get("ability_used_list", []),
            "process_info_list": kwargs.get("process_info_list", []),
            "process_objective": kwargs.get("process_objective", "")

        }

        self.process_list.append(new_process)
        self.current_process = new_process  # Update current_process to the newly added process
        self.parent.ability_list[2]["status"] = "enabled"
        self.parent.ability_list[0]["status"] = "enabled"

        return new_process

    def update_process(self, process_id: str, **kwargs) -> bool:
        """Update process info by ID and (optionally) update current_process."""
        for process in self.process_list:
            if process["id"] == process_id:
                process.update(kwargs)  # Update dict using update()
                self.current_process = process  # Update current_process to the latest process
                return True
        return False  # Return False if process ID is not found

    def get_process(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get process info by ID."""
        for process in self.process_list:
            if process["id"] == process_id:
                self.current_process = process  # If found, update current_process
                return process
        return None  # Return None if process ID is not found

    def get_current_process(self):
        process = self.current_process
        current_place = self.parent.get_current_place()
        current_position = self.parent.get_current_position()
        process_target = self.current_objective if self.current_objective else self.get_current_sub_task()["details"]

        if not process:
            process = self.add_process(current_place=current_place, current_position=current_position, process_target=process_target)
        else:
            if process.get("current_place") != current_place:
                process = self.add_process(current_place=current_place, current_position=current_position, process_target=process_target)

        return process

    async def process_task(self, **kwargs):
        try:
            async with self._process_lock:
                return await self._process_task_impl(**kwargs)
        except Exception as e:
            event = kwargs.get("event", "")
            action_requested = kwargs.get("action", "")
            logger.exception(f"process_task failed (event={event}, action={action_requested}): {e}")
            return None

    async def _process_task_impl(self, **kwargs):
        logger.info("[Step-05],Start process_task...")
        await self.pause_and_wait_for_resume()
        self.kwargs = kwargs
        action_requested = kwargs.get("action", "")
        event = kwargs.get("event", "")
        instruction = kwargs.get("instruction", "")

        human_send_flag = kwargs.get("human_send_flag", False)
        if self.parent.human_take_over:
            if action_requested == "process_activity":
                if not human_send_flag:
                    return

        if self.parent.stopping_ai_process_flag:
            self.parent.stop_AI_process_finished()
            return

        if not self.init_flag:
            self.init_task_mng()

        if action_requested == "process_activity":
            self.parent.write_on_going_process_to_pane(lt("Agent is thinking how to proceed current action.", "Agent is thinking how to proceed with the current action."))
            ask_content = kwargs.get("ask_content", self.get_current_objective())
            stop_review = True
            if not self.parent.human_take_over:
                if not stop_review:
                    if not self.reviewing_task:
                        self.review_task()
                        return
                    else:
                        self.reviewing_task = False

            item_to_achieved = ""
            if ask_content:
                item_to_achieved = ask_content

            self.js_task_manager.show_information(lt(f"Agent is thinking how to proceed:{item_to_achieved}", f"Agent is thinking how to proceed:{item_to_achieved}"))
            self.set_command_status("ask_agent_instruction_to_process_activity")

            asyncio.create_task(self.parent.ask_agent_instruction_to_process_activity(ask_content))

        elif event == "agent_instruction_to_process_activity_returned":
            # instruction_dict = json.loads(instruction)
            instruction_dict = ""
            if instruction_dict:
                function = ""
                objective_to_achieve = ""
            else:
                function = ""
                objective_to_achieve = ""

            activity_mapping = {
                'activity_find_people_from_list_to_talk': 'Find a people to talk',
                'activity_find_place_from_list_to_move': 'Find a place to move',
                'activity_find_tool_from_list_to_use': 'Find a tool to use'
            }

            # Use dict.get() safely to avoid KeyError
            function_str = activity_mapping.get(function, 'Unknown function:' + function)

            self.js_task_manager.show_information(lt(f"Agent return instruction:{function_str}.The target is:{objective_to_achieve}", f"Agent return instruction:{function_str}. The target is:{objective_to_achieve}"))
            self.set_command_status("")
            self.parent.parse_agent_instruction_for_process_activity(instruction)

        elif action_requested == "process_human_instruction":
            ask_content = kwargs.get("ask_content", "")

            self.set_command_status("ask_agent_instruction_to_process_human_instruction")

            asyncio.create_task(self.parent.ask_agent_instruction_to_process_human_instruction(ask_content))

        elif event == "agent_instruction_to_process_human_instruction_returned":
            self.set_command_status("")
            self.parent.parse_agent_instruction_for_process_human_instruction(instruction)

        elif event == "ask_agent_start_to_talk_to_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = robust_json_loads(result, default=None)
            ok, missing_keys = self._validate_people_selection_result(people_dict)
            if not ok:
                if self._retry_pick_people_selection(talk_type="communication", raw_result=result, missing_keys=missing_keys):
                    return
                return

            self._pick_people_format_retry["communication"] = 0
            nick_name = (people_dict.get("nick_name") or "").strip()
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent chose {result} to talk"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"] = result
            self.parent.handle_ask_agent_start_to_talk_to_a_people_result(result)

        elif event == "ask_agent_start_to_sell_to_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = robust_json_loads(result, default=None)
            ok, missing_keys = self._validate_people_selection_result(people_dict)
            if not ok:
                if self._retry_pick_people_selection(talk_type="sell", raw_result=result, missing_keys=missing_keys):
                    return
                return

            self._pick_people_format_retry["sell"] = 0
            nick_name = (people_dict.get("nick_name") or "").strip()
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent chose {result} to talk"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"] = result
            self.parent.handle_ask_agent_start_to_sell_to_a_people_result(result)

        elif event == "ask_agent_start_to_buy_from_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = robust_json_loads(result, default=None)
            ok, missing_keys = self._validate_people_selection_result(people_dict)
            if not ok:
                if self._retry_pick_people_selection(talk_type="buy", raw_result=result, missing_keys=missing_keys):
                    return
                return

            self._pick_people_format_retry["buy"] = 0
            nick_name = (people_dict.get("nick_name") or "").strip()
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent chose {result} to talk"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"] = result
            self.parent.handle_ask_agent_start_to_buy_from_a_people_result(result)

        elif event == "conversation_message_received":
            talk_history_str = kwargs.get("talk_history_str", "")

            if self.parent.talk_type == "sell":
                self.set_command_status("ask_agent_to_review_conversation_sell")
                asyncio.create_task(self.parent.ask_agent_to_review_conversation_sell(self.current_objective, talk_history_str))
            elif self.parent.talk_type == "buy":
                self.set_command_status("ask_agent_to_review_conversation_buy")
                asyncio.create_task(self.parent.ask_agent_to_review_conversation_buy(self.current_objective, talk_history_str))
            else:
                self.set_command_status("ask_agent_to_review_conversation")
                asyncio.create_task(self.parent.ask_agent_to_review_conversation(self.current_objective, talk_history_str))

        elif event == "ask_agent_to_review_conversation_returned":
            result = kwargs.get("result", "")
            self.parent.handle_agent_review_conversation_result(result)

        elif event == "ask_agent_to_review_conversation_sell_returned":
            result = kwargs.get("result", "")
            self.parent.handle_agent_review_conversation_sell_result(result)

        elif event == "ask_agent_to_review_conversation_buy_returned":
            result = kwargs.get("result", "")
            self.parent.handle_agent_review_conversation_buy_result(result)






    def set_command_status(self, status):
        self.parent.command_status = status

    def add_process_info_to_list(self, info):
        self.process_info_list.append(info)

        try:
            self._schedule_process_history_flush()
        except Exception:
            pass

        if len(self.process_info_list) < 50:
            return

        if self._process_info_compacting:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._compact_process_info_list())
        except RuntimeError:
            # Called from a sync context without a running event loop.
            # Fall back to trimming without summarization.
            self.process_info_list = self.process_info_list[-50:]

    def _schedule_process_history_flush(self):
        try:
            task = getattr(self, "_process_history_flush_task", None)
            if isinstance(task, asyncio.Task) and not task.done():
                return
        except Exception:
            pass

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        self._process_history_flush_task = loop.create_task(self._flush_process_history())

    async def _flush_process_history(self):
        await asyncio.sleep(0.1)
        try:
            self.parent.write_process_history_to_pane()
        except Exception:
            try:
                self.parent.write_task_process_to_pane("")
            except Exception:
                pass

    async def _compact_process_info_list(self):
        if self._process_info_compacting:
            return

        if len(self.process_info_list) < 50:
            return

        self._process_info_compacting = True
        try:
            items_to_summarize = list(self.process_info_list[:40])
            prompt = (
                "Summarize the following 40 process log entries into a single concise note.\n"
                "Requirements:\n"
                "- Output must be <= 250 tokens.\n"
                "- Keep key decisions, outcomes, and next steps.\n"
                "- Do not include the full raw logs.\n\n"
                "Entries:\n"
            )
            for idx, item in enumerate(items_to_summarize, 1):
                prompt += f"{idx}. {item}\n"

            summary = ""
            try:
                summary = await self.parent.chat_with_agent(
                    prompt,
                    conversation_suffix="process_info_compact",
                    use_tools=False,
                    use_memory=False,
                    use_knowledge_base=False,
                )
            except Exception as e:
                logger.warning("Failed to call agent for process log compaction: %s", e)
                summary = ""

            summary = (summary or "").strip()
            if not summary:
                # If summarization fails, keep only the newest 10 to avoid unbounded growth.
                self.process_info_list = self.process_info_list[-10:]
                return

            tail = list(self.process_info_list[-10:])
            self.process_info_list = [f"Summary: {summary}"] + tail
            logger.info(
                "Compacted process_info_list. summary_len=%s tail_len=%s",
                len(summary),
                len(tail),
            )
        finally:
            self._process_info_compacting = False

    def set_current_objective(self, content):
        self.current_objective = content

    def set_current_activity_objective(self, content):
        self.current_activity_objective = content

    def show_information(self, info, type_str="1"):
        self.js_task_manager.show_information(info, type_str)

    def write_on_going_process_to_pane(self, content):
        self.parent.write_on_going_process_to_pane(content)

    def write_task_process_to_pane(self, content):
        self.parent.write_task_process_to_pane(content)

    def write_thinking_process_to_pane(self, content, function_name=""):
        self.parent.write_thinking_process_to_pane(content, function_name)

    def show_status_on_map(self, status):
        self.parent.show_status_on_map(status)

    async def pause_and_wait_for_resume(self):
        """
        Pause and wait for resume (async version).
        Continue only when map_task_status == "started".
        """
        import asyncio

        while True:
            current_status = getattr(self.parent, 'map_task_status', None)

            # If status is started, continue
            if current_status == "started":
                logger.info("Task processing resumed, continuing execution...")
                break

            # If status is paused, wait for changes
            elif current_status == "paused":
                logger.debug("Task processing paused, waiting for resume...")
                await asyncio.sleep(0.5)  # Async wait; does not block the event loop

            # Otherwise (e.g. stopped), exit loop
            else:
                logger.info(f"Task processing stopped due to status: {current_status}")
                break
