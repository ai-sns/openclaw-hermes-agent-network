import json
import asyncio
from db.DBFactory import get_prompt_by_title, upsert_prompt_by_title
from runtime.i18n import lt
from typing import Dict, Any, Optional
from runtime.shared.utils import generate_random_id
import logging
from runtime.shared.utils import robust_json_loads
import re

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
        self._process_plan_summarizing = False
        self.reviewing_current_process = False
        self.reviewing_task = False

        self._process_history_flush_task = None

        self._process_info_since_compact = 0
        self._process_info_since_plan_summary = 0
        self._process_plan_summary_due = False
        self._resume_after_plan_summary = None

        self._process_info_since_tool_check = 0
        self._tool_check_due = False
        self._tool_checking = False
        self._resume_after_tool_check = None

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
        all_people = []
        try:
            all_people = list(self.parent.get_people_list() or [])
        except Exception:
            all_people = []

        people_list = None
        try:
            if hasattr(self.parent, "_get_filtered_people_list_for_talk_type"):
                people_list = self.parent._get_filtered_people_list_for_talk_type(talk_type)
        except Exception:
            people_list = None

        try:
            if (
                talk_type != "buy"
                and people_list is not None
                and hasattr(self.parent, "_maybe_notify_recommended_excluded_by_talk_type_filter")
            ):
                self.parent._maybe_notify_recommended_excluded_by_talk_type_filter(
                    talk_type=talk_type,
                    objective_text=objective_to_achieve,
                    all_people=all_people,
                    filtered_people=list(people_list or []),
                )
        except Exception:
            pass
        if not people_list:
            try:
                people_list = self.parent.get_people_list() or []
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
                "Missing/invalid keys: __missing_keys__. Previous raw output: __raw_result__"
            )
        strict_instruction = strict_instruction.replace("__missing_keys__", str(missing_keys))
        strict_instruction = strict_instruction.replace("__raw_result__", str(raw_result)[:300])
        content_prompt = f"{content_prompt}\n\n{strict_instruction}"

        logger.warning(
            f"Invalid people selection result, retrying (talk_type={talk_type}, retry={retry_count + 1}/3, missing={missing_keys})."
        )
        try:
            if hasattr(self.parent, "_instruction_total_count"):
                self.parent._instruction_total_count += 1
            if hasattr(self.parent, "_instruction_invalid_count"):
                self.parent._instruction_invalid_count += 1
            if hasattr(self.parent, "_update_iq_point_from_counters"):
                self.parent._update_iq_point_from_counters()
        except Exception:
            pass

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
        self._process_plan_summarizing = False
        self._process_info_since_compact = 0
        self._process_info_since_plan_summary = 0
        self._process_plan_summary_due = False
        self._resume_after_plan_summary = None

        self._process_info_since_tool_check = 0
        self._tool_check_due = False
        self._tool_checking = False
        self._resume_after_tool_check = None

        self.js_task_manager = self.parent.taskmng_js
        self.current_task_record = None

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
            self.parent.write_on_going_process_to_pane(lt("Thinking about the next action.", "Thinking about the next action."))
            ask_content = kwargs.get("ask_content", self.get_current_objective())
            tool_check_done = bool(kwargs.get("_tool_check_done", False))
            stop_review = True
            if not self.parent.human_take_over:
                if not stop_review:
                    if not self.reviewing_task:
                        self.review_task()
                        return
                    else:
                        self.reviewing_task = False

            if not tool_check_done:
                try:
                    self._process_info_since_tool_check += 1
                except Exception:
                    pass
                self._maybe_schedule_tool_check()
            if self._tool_check_due and (not self._tool_checking):
                self.show_status_on_map("using-tool")
                self.js_task_manager.show_information(lt(
                    "<b>🔮Using tools before action decision.</b>",
                    "<b>🔮Using tools before action decision.</b>",
                ))
                self._tool_checking = True
                self._tool_check_due = False
                self._resume_after_tool_check = {
                    "action": "process_activity",
                    "ask_content": ask_content,
                    "human_send_flag": human_send_flag,
                    "_tool_check_done": True,
                }
                asyncio.create_task(self.process_task(action="process_tool_check"))
                return

            if self._process_plan_summary_due and (not self._process_plan_summarizing):
                self.js_task_manager.show_information(lt(f"<b>Agent is updating plan and goals.</b>", f"<b>Agent is updating plan and goals.</b>"))
                self._process_plan_summarizing = True
                self._process_plan_summary_due = False
                self._resume_after_plan_summary = {
                    "action": "process_activity",
                    "ask_content": ask_content,
                    "human_send_flag": human_send_flag,
                }
                asyncio.create_task(self.process_task(action="process_plan_summary"))
                return

            counter = None
            try:
                counter = getattr(self.parent, "process_activity_counter", None)
                if counter is not None:
                    self.parent.process_activity_counter = counter + 1
            except Exception:
                counter = None

            try:
                if not bool(getattr(self.parent, "human_take_over", False)):
                    if hasattr(self.parent, "maybe_auto_reply_from_inbox"):
                        # Always check inbox first. maybe_auto_reply_from_inbox returns
                        # False quickly when inbox is empty, so removing the every-other-tick
                        # gating is safe and ensures freshly arrived messages (including the
                        # one that auto-started the engine) are processed on the very next
                        # tick instead of being skipped for an unrelated process_activity.
                        if await self.parent.maybe_auto_reply_from_inbox():
                            return
            except Exception:
                logger.exception("Inbox auto-reply hook failed")

            suffix = f"[#{counter+1}]" if counter is not None else ""
            msg = f"<b>🤔Agent is thinking about the next action.{suffix}</b>"
            self.js_task_manager.show_information(lt(msg, msg))
            self.set_command_status("ask_agent_instruction_to_process_activity")

            asyncio.create_task(self.parent.ask_agent_instruction_to_process_activity(ask_content))

        elif action_requested == "process_plan_summary":
            plan_manage_prompt = (get_prompt_by_title("__plan_manage__") or "").strip()
            current_goals = (get_prompt_by_title("__plan_goals__") or "").strip()
            current_long_goals, current_short_goals = self._extract_goal_sections(current_goals)
            items = list(self.process_info_list or [])
            items = items[-60:] if len(items) > 60 else items
            process_log = "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(items))

            output_req = (get_prompt_by_title("__plan_summary_output_requirements__") or "").strip()
            if not output_req:
                output_req = (
                    "Output requirements:\n"
                    "- Provide updated goals only.\n"
                    "- Include BOTH sections with these exact labels:\n"
                    "  Long-Term Goals:\n"
                    "  Short-Term Goals:\n"
                    "- Do NOT include any other sections such as Changes Made/Reasoning/Next Recommended Actions."
                )
            msg_parts = [
                "Current Long-Term Goals (may be empty):",
                (current_long_goals or "").strip() or "(empty)",
                "Current Short-Term Goals (may be empty):",
                (current_short_goals or "").strip() or "(empty)",
                "Process log entries:",
                process_log,
                "\n" + output_req + "\n",
            ]
            question = "\n\n".join([p for p in msg_parts if p is not None])

            self.set_command_status("ask_agent_process_plan_summary")
            asyncio.create_task(self.parent.ask_agent_and_get_instruction(question, plan_manage_prompt))

        elif action_requested == "process_tool_check":
            # Fire and return to release the _process_lock immediately.
            # _run_tool_check_before_activity will resume process_activity on completion.
            asyncio.create_task(self._run_tool_check_before_activity())

        elif event == "agent_instruction_to_process_activity_returned":


            self.set_command_status("")
            self.parent.parse_agent_instruction_for_process_activity(instruction)

        elif event == "ask_agent_process_plan_summary_returned":
            result = kwargs.get("result", "")
            try:
                long_goals, short_goals = self._extract_goal_sections((result or "").strip())
            except Exception:
                long_goals, short_goals = "", ""

            if not long_goals and not short_goals:
                logger.warning(
                    "Process plan summary did not contain goal sections; skipping __plan_goals__ update. raw_result_head=%s",
                    (result or "")[:300],
                )
            else:
                next_content = (
                    "Long-Term Goals:\n"
                    f"{(long_goals or '').strip()}\n\n"
                    "Short-Term Goals:\n"
                    f"{(short_goals or '').strip()}\n"
                )
                ok = False
                try:
                    ok = bool(upsert_prompt_by_title("__plan_goals__", next_content))
                except Exception as e:
                    logger.warning("Failed to update __plan_goals__ prompt: %s", e)
                    ok = False

                if ok:
                    logger.info("Updated __plan_goals__ from process plan summary")

            self._process_plan_summarizing = False
            self.set_command_status("")

            resume_payload = self._resume_after_plan_summary
            self._resume_after_plan_summary = None
            if isinstance(resume_payload, dict) and resume_payload:
                asyncio.create_task(self.process_task(**resume_payload))
            else:
                try:
                    if bool(getattr(self.parent, "_human_command_inflight", False)) and hasattr(self.parent, "_maybe_finish_human_command_if_idle"):
                        self.parent._maybe_finish_human_command_if_idle(ask_content=self.get_current_objective())
                    else:
                        asyncio.create_task(self.process_task(action="process_activity", ask_content=self.get_current_objective()))
                except Exception:
                    asyncio.create_task(self.process_task(action="process_activity", ask_content=self.get_current_objective()))

        elif action_requested == "process_human_instruction":
            ask_content = kwargs.get("ask_content", "")

            counter = None
            try:
                counter = getattr(self.parent, "process_activity_counter", None)
                if counter is not None:
                    self.parent.process_activity_counter = counter + 1
            except Exception:
                counter = None

            try:
                suffix = f"[#{counter + 1}]" if counter is not None else ""
                msg = f"<b>🤔Agent is thinking the human instruction.{suffix}</b>"
                if self.js_task_manager:
                    self.js_task_manager.show_information(lt(msg, msg))
            except Exception:
                logger.exception("Failed to show process_human_instruction status on UI")

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
            self.parent.write_on_going_process_to_pane(f"Chatting with {nick_name}")
            self.js_task_manager.show_information(lt(f"<b>Agent selected {nick_name} for communication.</b>", f"<b>Agent selected {nick_name} for communication.</b>"))
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
            self.parent.write_on_going_process_to_pane(f"Marketing to {nick_name}")
            self.js_task_manager.show_information(lt(f"<b>Agent select {nick_name} to promote to.</b>", f"<b>Agent select {nick_name} to promote to.</b>"))
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
            self.parent.write_on_going_process_to_pane(f"Purchasing from {nick_name}")
            self.js_task_manager.show_information(lt(f"<b>Agent select {nick_name} to buy from.</b>", f"<b>Agent select {nick_name} to buy from.</b>"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"] = result
            self.parent.handle_ask_agent_start_to_buy_from_a_people_result(result)

        elif event == "conversation_message_received":
            talk_history_str = kwargs.get("talk_history_str", "")
            tool_check_done = kwargs.get("_tool_check_done", False)

            effective_talk_type = ""
            try:
                active = getattr(self.parent, "active_conversation", None) or {}
                if isinstance(active, dict):
                    effective_talk_type = (active.get("talk_type") or "").strip()
            except Exception:
                effective_talk_type = ""
            if not effective_talk_type:
                effective_talk_type = (getattr(self.parent, "talk_type", "") or "").strip()

            # Run tool check before review if enabled (only once per message)
            if (not tool_check_done) and bool(getattr(self.parent, "tool_check_before_review_enabled", False)):
                asyncio.create_task(self._run_tool_check_then_review(
                    talk_history_str=talk_history_str,
                    effective_talk_type=effective_talk_type,
                ))
                return

            if effective_talk_type == "sell":
                self.set_command_status("ask_agent_to_review_conversation_sell")
                asyncio.create_task(self.parent.ask_agent_to_review_conversation_sell(self.current_objective, talk_history_str))

            elif effective_talk_type == "buy":
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

        self._process_info_since_compact += 1
        self._process_info_since_plan_summary += 1
        self._process_info_since_tool_check += 1


        self._maybe_schedule_process_plan_summary()
        self._maybe_schedule_process_info_compaction()

    def _resolve_process_info_compact_every_n(self) -> int:
        try:
            v = int(getattr(self.parent, "process_info_compact_every_n", 50))
        except Exception:
            v = 50
        return max(0, v)

    def _resolve_process_info_plan_summary_every_n(self) -> int:
        try:
            v = int(getattr(self.parent, "process_info_plan_summary_every_n", 5))
        except Exception:
            v = 5
        return max(0, v)

    def _maybe_schedule_process_info_compaction(self):
        compact_every = self._resolve_process_info_compact_every_n()
        if compact_every <= 0:
            return

        if self._process_info_since_compact < compact_every:
            return

        if self._process_info_compacting:
            return

        self._process_info_since_compact = 0

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._compact_process_info_list())
        except RuntimeError:
            keep = max(50, compact_every)
            self.process_info_list = self.process_info_list[-keep:]

    def _maybe_schedule_process_plan_summary(self):
        summary_every = self._resolve_process_info_plan_summary_every_n()
        if summary_every <= 0:
            return

        if self._process_info_since_plan_summary < summary_every:
            return

        if self._process_plan_summarizing:
            return

        if getattr(self, "_process_plan_summary_due", False):
            return

        self._process_info_since_plan_summary = 0

        self._process_plan_summary_due = True
        logger.info(
            "Marked process plan summary due (every_n=%s, process_info_len=%s)",
            summary_every,
            len(getattr(self, "process_info_list", []) or []),
        )

    def _resolve_tool_check_every_n(self) -> int:
        try:
            v = int(getattr(self.parent, "tool_check_every_n", 0))
        except Exception:
            v = 0
        return max(0, v)

    def _maybe_schedule_tool_check(self):
        every_n = self._resolve_tool_check_every_n()
        if every_n <= 0:
            return

        if self._process_info_since_tool_check < every_n:
            return

        if self._tool_checking:
            return

        if getattr(self, "_tool_check_due", False):
            return

        self._process_info_since_tool_check = 0

        self._tool_check_due = True
        logger.info(
            "Marked tool check due (every_n=%s, process_info_len=%s)",
            every_n,
            len(getattr(self, "process_info_list", []) or []),
        )

    async def _run_tool_check_before_activity(self):
        """Run tool check before process_activity using chat_with_agent(use_tools=True).
        On completion (success or failure), always resumes the original process_activity flow."""
        tool_result = ""
        try:
            tool_prompt = (get_prompt_by_title("__tool_check_before_activity__") or "").strip()
            if not tool_prompt:
                logger.warning("Tool check prompt __tool_check_before_activity__ not found, skipping tool check")
                return

            current_goals = (get_prompt_by_title("__plan_goals__") or "").strip()
            items = list(self.process_info_list or [])
            items = items[-30:] if len(items) > 30 else items
            process_log = "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(items))

            is_remote = self.parent.is_current_agent_remote()

            context_parts = [
                tool_prompt,
                "\n--- Current Context ---",
                f"Current place: {getattr(self.parent, 'current_place', 'unknown')}",
                f"Current objective: {self.current_objective or '(none)'}",
                f"Goals:\n{current_goals or '(none)'}",
                f"Recent process log:\n{process_log or '(empty)'}",
            ]

            if is_remote:
                # Remote agent: wrap with task-oriented instructions; do not use local tools
                remote_instr = (get_prompt_by_title("__remote_agent_tool_check_activity__") or "").strip()
                if not remote_instr:
                    remote_instr = (
                        "--- Instructions for Remote Agent ---\n"
                        "Based on the context above, use any tools or capabilities you have "
                        "to gather information that would help decide the next action.\n"
                        "Return only the result. If no tool call is needed, respond with NO_TOOL_NEEDED."
                    )
                context_parts.append("\n" + remote_instr)

            question = "\n".join(context_parts)

            tool_result = await self.parent.chat_with_agent(
                question,
                conversation_suffix="tool_check_activity",
                use_tools=(not is_remote),
                use_memory=False,
                use_knowledge_base=False,
            )

        except Exception as e:
            logger.warning("Tool check before activity failed: %s", e)
            tool_result = ""
        finally:
            self._tool_checking = False

            # Record tool result into process_info_list if meaningful
            tool_result = (tool_result or "").strip()
            if tool_result and "NO_TOOL_NEEDED" not in tool_result.upper():
                entry = f"[Tool Check Result] {tool_result[:500]}"
                self.process_info_list.append(entry)
                logger.info("Tool check result added to process info list")

            # Resume the original process_activity flow
            resume_payload = self._resume_after_tool_check
            self._resume_after_tool_check = None
            if isinstance(resume_payload, dict) and resume_payload:
                asyncio.create_task(self.process_task(**resume_payload))
            else:
                try:
                    if bool(getattr(self.parent, "_human_command_inflight", False)) and hasattr(self.parent, "_maybe_finish_human_command_if_idle"):
                        self.parent._maybe_finish_human_command_if_idle(ask_content=self.get_current_objective())
                    else:
                        asyncio.create_task(self.process_task(action="process_activity", ask_content=self.get_current_objective()))
                except Exception:
                    asyncio.create_task(self.process_task(action="process_activity", ask_content=self.get_current_objective()))

    async def _inspect_command_forms(
        self,
        a2a_mgr,
        peer_jid: str,
        commands: list,
        per_cmd_timeout: float = 10.0,
    ) -> None:
        """Probe each discovered ad-hoc command for its XEP-0004 form schema.

        Mutates each command dict in ``commands`` by attaching a ``form`` key
        ({"title": str, "fields": [{"var","type","label","required","value"}]})
        when inspection succeeds. Failures are logged and the command dict is
        left untouched — rendering will simply omit the form section for that
        command, so the flow degrades gracefully.

        All inspections run in parallel to keep the prompt-building latency
        bounded roughly to ``per_cmd_timeout``.
        """
        if not commands:
            return

        async def _one(cmd: dict) -> None:
            node = cmd.get("node")
            if not node:
                return
            try:
                res = await asyncio.wait_for(
                    a2a_mgr.call_adhoc_command(
                        peer_jid=peer_jid,
                        command_node=node,
                        form_data=None,
                        inspect_only=True,
                        timeout_per_resource=4.0,
                    ),
                    timeout=per_cmd_timeout,
                )
            except Exception as e:
                logger.info(
                    "[XMPP-A2A][DIAG] inspect_command_forms: node=%s failed: %s",
                    node, e,
                )
                return
            if isinstance(res, dict) and res.get("ok") and isinstance(res.get("form"), dict):
                cmd["form"] = res["form"]
                logger.info(
                    "[XMPP-A2A][DIAG] inspect_command_forms: node=%s fields=%d",
                    node, len(res["form"].get("fields") or []),
                )

        await asyncio.gather(*(_one(c) for c in commands), return_exceptions=True)

    def _build_a2a_tool_guidance(self, card_json: str, discovered_commands: list = None) -> str:
        """Build an A2A tool usage guidance section for the LLM prompt.

        Dynamically lists discovered ad-hoc commands and shows the single
        generic a2a_xmpp_adhoc tool usage pattern.

        Args:
            card_json: The agent card JSON string
            discovered_commands: List from discover_peer_adhoc_commands (optional)

        Returns:
            A guidance string, or empty string if no transport available
        """
        try:
            card = json.loads(card_json) if card_json else {}
        except Exception:
            card = {}

        active = getattr(self.parent, "active_conversation", None) or {}

        # Extract A2A URL from card; fall back to active_conversation endpoint
        a2a_url = (card.get("url") or "").strip()
        if not a2a_url:
            a2a_url = (active.get("a2a_endpoint") or "").strip()

        # Extract peer JID from active conversation
        peer_jid = (active.get("account") or "").strip()
        has_jid = bool(peer_jid and "@" in peer_jid)

        if not a2a_url and not has_jid:
            return ""

        parts = [
            "\n--- A2A Tool Available (HIGH PRIORITY) ---",
            "If the peer's most recent message asks you to use an A2A / XMPP ad-hoc command "
            "(e.g. exchange business card, invoke a discovered skill), you MUST call the "
            "a2a_xmpp_adhoc tool below with the matching command_node — DO NOT reply with text "
            "and DO NOT call unrelated tools (such as get_system_info).",
        ]

        # HTTP transport (run_doc_skill)
        if a2a_url:
            skills = card.get("skills") or []
            skill_ids = [s.get("id", "") for s in skills if isinstance(s, dict) and s.get("id")]
            skills_hint = ", ".join(skill_ids) if skill_ids else "(see agent card above)"
            parts.append(
                "Option A — HTTP (use when peer has a reachable URL):\n"
                "To send a task:\n"
                '  run_doc_skill(skill_key="a2a_call", params={\n'
                f'    "url": "{a2a_url}",\n'
                '    "method": "tasks/send",\n'
                '    "message_text": "<your message>",\n'
                f'    "skill_id": "<one of: {skills_hint}>"\n'
                "  })"
            )

        # HTTP JSON-RPC transport — list any skills declaring transport=http_jsonrpc
        try:
            jsonrpc_skills = [
                s for s in (card.get("skills") or [])
                if isinstance(s, dict) and str(s.get("transport", "")).lower() == "http_jsonrpc"
            ]
        except Exception:
            jsonrpc_skills = []
        if jsonrpc_skills:
            parts.append(
                "Option C — HTTP JSON-RPC (peer declares one or more skills with transport='http_jsonrpc'):\n"
                "Use a2a_jsonrpc_call to invoke these directly. The tool wraps your params in a JSON-RPC 2.0 envelope.\n"
                "Usage:\n"
                '  a2a_jsonrpc_call(endpoint="<skill.endpoint>", method="<skill.method>", params={...})'
            )
            for sk in jsonrpc_skills:
                sid = sk.get("id", "")
                sname = sk.get("name", "")
                ep = sk.get("endpoint") or a2a_url
                meth = sk.get("method", "")
                desc = (sk.get("description") or "").strip()
                if len(desc) > 200:
                    desc = desc[:200].rstrip() + "..."
                parts.append(f'  - id="{sid}" name="{sname}"')
                if desc:
                    parts.append(f"      description: {desc}")
                parts.append(f'      endpoint="{ep}" method="{meth}"')
                schema = sk.get("params_schema")
                if isinstance(schema, dict) and schema:
                    try:
                        parts.append("      params_schema: " + json.dumps(schema, ensure_ascii=False))
                    except Exception:
                        pass
                example = sk.get("example_request")
                if isinstance(example, dict) and example:
                    try:
                        params_example = example.get("params") or {}
                        parts.append("      example params: " + json.dumps(params_example, ensure_ascii=False))
                    except Exception:
                        pass

        # XMPP transport — generic ad-hoc commands
        if has_jid:
            parts.append(
                f"Option B — XMPP Ad-hoc Commands (peer_jid: {peer_jid}):\n"
                "Use a2a_xmpp_adhoc to invoke any ad-hoc command on the peer.\n"
                "Usage:\n"
                f'  a2a_xmpp_adhoc(peer_jid="{peer_jid}", command_node="<node>", form_data={{...}})\n'
                "To inspect form fields before calling:\n"
                f'  a2a_xmpp_adhoc(peer_jid="{peer_jid}", command_node="<node>", inspect_only=true)'
            )

            # List discovered commands (with form schemas when available)
            cmds = discovered_commands or []
            if cmds:
                parts.append("Discovered commands on this peer:")
                for cmd in cmds:
                    node = cmd.get("node")
                    if not node:
                        continue
                    desc = cmd.get("description") or cmd.get("name") or ""
                    parts.append(f'  - node="{node}" name="{cmd.get("name", "")}" ({desc})')
                    form_meta = cmd.get("form") if isinstance(cmd.get("form"), dict) else None
                    if form_meta is None:
                        parts.append("      form_data: (form schema unavailable — use inspect_only=true before submitting)")
                        continue
                    fields = (form_meta or {}).get("fields") or []
                    if not fields:
                        parts.append("      form_data: (no form fields — call without form_data)")
                        continue
                    required = [f for f in fields if f.get("required")]
                    optional = [f for f in fields if not f.get("required")]

                    def _fmt(f: dict) -> str:
                        var = f.get("var") or ""
                        ftype = f.get("type") or "text-single"
                        label = (f.get("label") or "").strip()
                        label_part = f" — {label}" if label else ""
                        return f'"{var}" ({ftype}){label_part}'

                    if required:
                        parts.append("      required form_data: " + ", ".join(_fmt(f) for f in required))
                    if optional:
                        parts.append("      optional form_data: " + ", ".join(_fmt(f) for f in optional))
            else:
                parts.append("(No commands discovered yet. Use inspect_only=true to explore.)")

        parts.append("--- End A2A Tool ---\n")
        return "\n".join(parts)

    async def _fetch_peer_agent_card(self) -> str:
        """Fetch the agent card JSON from the peer.

        Priority:
          1. HTTP GET via the fetch_agent_card skill (uses a2a_endpoint)
          2. XMPP PEP fallback — read the peer's urn:xmpp:a2a:agentcard node
        """
        active = getattr(self.parent, "active_conversation", None) or {}

        # ── Attempt 1: HTTP via a2a_endpoint ────────────────────────────────
        endpoint = (active.get("a2a_endpoint") or "").strip()
        if endpoint:
            try:
                from runtime.modules.skills_registry.service import get_docskills_service
                svc = get_docskills_service()
                result = await svc.run_skill("fetch_agent_card", {"url": endpoint})

                if not result or not result.get("success"):
                    error_msg = result.get("error", "unknown") if result else "no result"
                    logger.debug("fetch_agent_card skill failed: %s", error_msg)
                else:
                    # The python_file runner puts parsed stdout JSON into result.result.parsed
                    inner = result.get("result") or {}
                    parsed = inner.get("parsed") or {}
                    if not isinstance(parsed, dict):
                        # Fallback: try parsing stdout directly
                        stdout = (inner.get("stdout") or "").strip()
                        if stdout:
                            try:
                                parsed = json.loads(stdout)
                            except Exception:
                                parsed = {}

                    if parsed.get("ok"):
                        card = (parsed.get("card") or "").strip()
                        source = parsed.get("source", "")
                        if card:
                            logger.debug("Agent card fetched via HTTP skill (source=%s, %d chars)", source, len(card))
                            return card

                    skill_error = parsed.get("error", "")
                    if skill_error:
                        logger.debug("fetch_agent_card skill returned error: %s", skill_error)
            except Exception as e:
                logger.warning("_fetch_peer_agent_card HTTP skill error: %s", e)

        # ── Attempt 2: XMPP PEP fallback ───────────────────────────────────
        peer_jid = (active.get("account") or "").strip()
        if peer_jid and "@" in peer_jid:
            try:
                from runtime.apps.sns.xmpp_client import XMPPClientManager
                client = XMPPClientManager.get_instance().get_client()
                if client and client.is_client_connected():
                    a2a_mgr = getattr(client, "_a2a_manager", None)
                    if a2a_mgr is not None:
                        card_dict = await a2a_mgr.fetch_peer_agent_card_pep(peer_jid)
                        if card_dict and isinstance(card_dict, dict):
                            card_str = json.dumps(card_dict, ensure_ascii=False)
                            logger.info(
                                "Agent card fetched via XMPP PEP from %s (%d chars)",
                                peer_jid,
                                len(card_str),
                            )
                            return card_str
                    else:
                        logger.debug("XMPP A2A manager not initialized, skipping PEP fallback")
                else:
                    logger.debug("XMPP client not connected, skipping PEP fallback")
            except Exception as e:
                logger.warning("_fetch_peer_agent_card XMPP PEP fallback error: %s", e)

        return ""

    @staticmethod
    def _extract_a2a_call_json(raw_response: str):
        """Extract a2a_call/a2a_calls JSON from remote agent response.

        Returns (parsed_obj, start_idx, end_idx) or (None, -1, -1) if not found.
        Only matches JSON objects containing 'a2a_call', 'a2a_calls', or 'command_node' keys.
        """
        import re as _re

        _A2A_KEYS = {"a2a_call", "a2a_calls", "command_node"}

        def _has_a2a_key(obj):
            return isinstance(obj, dict) and bool(_A2A_KEYS & set(obj.keys()))

        # Strategy 1: fenced JSON block  ```json ... ``` or ``` ... ```
        fence_pattern = _re.compile(r'```(?:json)?\s*\n(.*?)\n\s*```', _re.DOTALL)
        for m in fence_pattern.finditer(raw_response):
            try:
                parsed = json.loads(m.group(1))
                if _has_a2a_key(parsed):
                    return (parsed, m.start(), m.end())
            except (json.JSONDecodeError, ValueError):
                continue

        # Strategy 2: balanced { ... } scan
        i = 0
        text_len = len(raw_response)
        while i < text_len:
            if raw_response[i] == '{':
                depth = 0
                j = i
                in_string = False
                escape_next = False
                while j < text_len:
                    ch = raw_response[j]
                    if escape_next:
                        escape_next = False
                    elif ch == '\\' and in_string:
                        escape_next = True
                    elif ch == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                candidate = raw_response[i:j + 1]
                                try:
                                    parsed = json.loads(candidate)
                                    if _has_a2a_key(parsed):
                                        return (parsed, i, j + 1)
                                except (json.JSONDecodeError, ValueError):
                                    pass
                                break
                    j += 1
            i += 1

        return (None, -1, -1)

    @staticmethod
    def _extract_jsonrpc_call_json(raw_response: str):
        """Extract jsonrpc_call/jsonrpc_calls JSON from remote agent response.

        Returns (parsed_obj, start_idx, end_idx) or (None, -1, -1) if not found.
        Only matches JSON objects containing 'jsonrpc_call' or 'jsonrpc_calls' keys.
        """
        import re as _re

        _JSONRPC_KEYS = {"jsonrpc_call", "jsonrpc_calls"}

        def _has_key(obj):
            return isinstance(obj, dict) and bool(_JSONRPC_KEYS & set(obj.keys()))

        # Strategy 1: fenced JSON block  ```json ... ``` or ``` ... ```
        fence_pattern = _re.compile(r'```(?:json)?\s*\n(.*?)\n\s*```', _re.DOTALL)
        for m in fence_pattern.finditer(raw_response):
            try:
                parsed = json.loads(m.group(1))
                if _has_key(parsed):
                    return (parsed, m.start(), m.end())
            except (json.JSONDecodeError, ValueError):
                continue

        # Strategy 2: balanced { ... } scan
        i = 0
        text_len = len(raw_response)
        while i < text_len:
            if raw_response[i] == '{':
                depth = 0
                j = i
                in_string = False
                escape_next = False
                while j < text_len:
                    ch = raw_response[j]
                    if escape_next:
                        escape_next = False
                    elif ch == '\\' and in_string:
                        escape_next = True
                    elif ch == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                candidate = raw_response[i:j + 1]
                                try:
                                    parsed = json.loads(candidate)
                                    if _has_key(parsed):
                                        return (parsed, i, j + 1)
                                except (json.JSONDecodeError, ValueError):
                                    pass
                                break
                    j += 1
            i += 1

        return (None, -1, -1)

    async def _execute_remote_jsonrpc_requests(
        self,
        raw_response: str,
        *,
        max_calls: int = 3,
        per_call_timeout: float = 30.0,
    ):
        """Parse remote agent response for jsonrpc_call JSON, validate, execute locally.

        Returns:
            (jsonrpc_result_text, cleaned_remote_text) tuple.
            - jsonrpc_result_text: formatted execution result string, or None.
            - cleaned_remote_text: raw_response with the jsonrpc JSON block removed.
        """
        obj, start, end = self._extract_jsonrpc_call_json(raw_response)
        if obj is None:
            return (None, raw_response)

        # Normalize to list of requests
        if "jsonrpc_calls" in obj and isinstance(obj["jsonrpc_calls"], list):
            requests = obj["jsonrpc_calls"]
        elif "jsonrpc_call" in obj and isinstance(obj["jsonrpc_call"], dict):
            requests = [obj["jsonrpc_call"]]
        else:
            return (None, raw_response)

        # Validate each request (basic structural checks only)
        valid_requests = []
        for req in requests:
            if not isinstance(req, dict):
                logger.info("[A2A-JSONRPC] remote jsonrpc request rejected: not a dict")
                continue
            req_endpoint = (req.get("endpoint") or "").strip()
            req_method = (req.get("method") or "").strip()
            req_params = req.get("params")

            if not req_endpoint:
                logger.warning("[A2A-JSONRPC] remote jsonrpc request rejected: empty endpoint")
                continue
            if not req_method:
                logger.warning("[A2A-JSONRPC] remote jsonrpc request rejected: empty method")
                continue
            if req_params is not None and not isinstance(req_params, dict):
                logger.warning("[A2A-JSONRPC] remote jsonrpc request rejected: params is not dict or None")
                continue

            valid_requests.append({"endpoint": req_endpoint, "method": req_method, "params": req_params})
            if len(valid_requests) >= max_calls:
                break

        if not valid_requests:
            logger.info("[A2A-JSONRPC] remote jsonrpc: no valid requests after validation")
            return (None, raw_response)

        # Execute via the same HTTP POST logic as _execute_a2a_jsonrpc_call
        async def _exec_one(req_item):
            import uuid as _uuid
            import urllib.request
            import urllib.error

            endpoint = req_item["endpoint"]
            method = req_item["method"]
            params = req_item["params"] or {}
            rpc_id = _uuid.uuid4().hex[:12]
            envelope = {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "method": method,
                "params": params,
            }
            logger.info(
                "[A2A-JSONRPC] remote proxy call: endpoint=%s method=%s",
                endpoint, method,
            )

            def _do_post():
                body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
                http_req = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(http_req, timeout=int(per_call_timeout)) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
                except urllib.error.HTTPError as he:
                    try:
                        raw = he.read().decode("utf-8", errors="replace")
                    except Exception:
                        raw = ""
                    return {"ok": False, "error": f"HTTP {he.code}: {he.reason}", "body": raw}
                except Exception as e:
                    return {"ok": False, "error": str(e)}

                try:
                    parsed = json.loads(raw)
                except Exception:
                    return {"ok": True, "raw": raw}

                if isinstance(parsed, dict) and "error" in parsed and parsed.get("error"):
                    return {"ok": False, "jsonrpc_error": parsed["error"], "response": parsed}
                return {"ok": True, "response": parsed}

            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(_do_post),
                    timeout=per_call_timeout,
                )
                logger.info("[A2A-JSONRPC] remote proxy call: method=%s status=ok", method)
                return {"method": method, "endpoint": endpoint, "status": "ok", "data": result}
            except asyncio.TimeoutError:
                logger.warning("[A2A-JSONRPC] remote proxy call: method=%s timeout", method)
                return {"method": method, "endpoint": endpoint, "status": "error", "error": f"timeout after {per_call_timeout:.0f}s"}
            except Exception as exc:
                logger.warning("[A2A-JSONRPC] remote proxy call: method=%s error=%s", method, exc)
                return {"method": method, "endpoint": endpoint, "status": "error", "error": str(exc)}

        results = await asyncio.gather(*[_exec_one(r) for r in valid_requests])

        # Format result text
        lines = ["[Local JSON-RPC Proxy Execution Result]"]
        for res in results:
            lines.append(f"- method={res['method']} endpoint={res['endpoint']} status={res['status']}")
            if res["status"] == "ok":
                data = res.get("data")
                if isinstance(data, dict):
                    try:
                        lines.append(f"    result: {json.dumps(data, ensure_ascii=False)}")
                    except Exception:
                        lines.append(f"    result: {data}")
                elif data is not None:
                    lines.append(f"    result: {data}")
            elif res.get("error"):
                lines.append(f"    error: {res['error']}")

        jsonrpc_text = "\n".join(lines)
        # Clean: remove the jsonrpc JSON block from raw response
        cleaned = (raw_response[:start] + raw_response[end:]).strip()
        return (jsonrpc_text, cleaned)

    async def _execute_remote_a2a_requests(
        self,
        raw_response: str,
        a2a_mgr,
        allowed_peer_jid: str,
        discovered_commands: list,
        *,
        max_calls: int = 3,
        per_call_timeout: float = 30.0,
        adhoc_timeout_per_resource: float = 12.0,
    ):
        """Parse remote agent response for a2a_call JSON, validate, execute locally.

        Returns:
            (adhoc_result_text, cleaned_remote_text) tuple.
            - adhoc_result_text: formatted execution result string, or None if nothing executed.
            - cleaned_remote_text: raw_response with the a2a JSON block removed.
        """
        obj, start, end = self._extract_a2a_call_json(raw_response)
        if obj is None:
            return (None, raw_response)

        # Normalize to list of requests
        if "a2a_calls" in obj and isinstance(obj["a2a_calls"], list):
            requests = obj["a2a_calls"]
        elif "a2a_call" in obj and isinstance(obj["a2a_call"], dict):
            requests = [obj["a2a_call"]]
        elif "command_node" in obj:
            requests = [obj]
        else:
            return (None, raw_response)

        # Build whitelist
        allowed_nodes = {c.get("node") for c in discovered_commands if c.get("node")}

        # Validate each request
        valid_requests = []
        for req in requests:
            if not isinstance(req, dict):
                logger.info("[XMPP-A2A] remote a2a request rejected: not a dict")
                continue
            req_peer = (req.get("peer_jid") or "").strip() or allowed_peer_jid
            req_node = (req.get("command_node") or "").strip()
            req_form = req.get("form_data")

            if req_peer != allowed_peer_jid:
                logger.warning("[XMPP-A2A] remote a2a request rejected: peer_jid=%s != allowed=%s", req_peer, allowed_peer_jid)
                continue
            if req_node not in allowed_nodes:
                logger.warning("[XMPP-A2A] remote a2a request rejected: command_node=%s not in whitelist", req_node)
                continue
            if req_form is not None and not isinstance(req_form, dict):
                logger.warning("[XMPP-A2A] remote a2a request rejected: form_data is not dict or None")
                continue

            valid_requests.append({"peer_jid": req_peer, "command_node": req_node, "form_data": req_form})
            if len(valid_requests) >= max_calls:
                break

        if not valid_requests:
            logger.info("[XMPP-A2A] remote a2a: no valid requests after validation")
            return (None, raw_response)

        # Execute in parallel with timeout
        async def _exec_one(req_item):
            node = req_item["command_node"]
            try:
                result = await asyncio.wait_for(
                    a2a_mgr.call_adhoc_command(
                        req_item["peer_jid"], node,
                        form_data=req_item["form_data"],
                        timeout_per_resource=adhoc_timeout_per_resource,
                    ),
                    timeout=per_call_timeout,
                )
                logger.info("[XMPP-A2A] remote a2a call_adhoc: node=%s status=ok", node)
                return {"node": node, "status": "ok", "data": result}
            except asyncio.TimeoutError:
                logger.warning("[XMPP-A2A] remote a2a call_adhoc: node=%s timeout after %.0fs", node, per_call_timeout)
                return {"node": node, "status": "error", "error": f"timeout after {per_call_timeout:.0f}s"}
            except Exception as exc:
                logger.warning("[XMPP-A2A] remote a2a call_adhoc: node=%s error=%s", node, exc)
                return {"node": node, "status": "error", "error": str(exc)}

        results = await asyncio.gather(*[_exec_one(r) for r in valid_requests])

        # Format result text
        lines = ["[Local A2A Ad-hoc Execution Result]"]
        any_success = False
        for res in results:
            lines.append(f"- node={res['node']} status={res['status']}")
            if res["status"] == "ok" and isinstance(res.get("data"), dict):
                any_success = True
                for k, v in res["data"].items():
                    lines.append(f"    {k}: {v}")
            elif res["status"] == "ok" and res.get("data"):
                any_success = True
                lines.append(f"    {res['data']}")
            elif res.get("error"):
                lines.append(f"    error: {res['error']}")

        if not any_success and all(r["status"] == "error" for r in results):
            # All failed — still return result so caller can decide
            pass

        adhoc_text = "\n".join(lines)
        # Clean: remove the a2a JSON block from raw response
        cleaned = (raw_response[:start] + raw_response[end:]).strip()
        return (adhoc_text, cleaned)

    async def _run_tool_check_then_review(self, *, talk_history_str: str, effective_talk_type: str):
        """Run tool check before conversation review using chat_with_agent(use_tools=True).
        Runs outside the _process_lock. On completion, re-dispatches conversation_message_received
        with the enriched talk_history_str so the review proceeds normally."""
        logger.info("[XMPP-A2A][DIAG] tool_check_review: ENTER talk_type=%s history_len=%d", effective_talk_type, len(talk_history_str or ""))
        # Safety: skip if no active conversation account (nothing meaningful to check)
        active = getattr(self.parent, "active_conversation", None) or {}
        if not (active.get("account") or "").strip():
            logger.info("[XMPP-A2A] tool_check_review: no active conversation account, skipping tool check")
            asyncio.create_task(self.process_task(
                event="conversation_message_received",
                talk_history_str=talk_history_str,
                _tool_check_done=True,
            ))
            return
        logger.info("[XMPP-A2A][DIAG] tool_check_review: active_conversation account=%s a2a_endpoint=%s", active.get("account"), active.get("a2a_endpoint"))

        tool_context = ""
        # Hoist key variables so they are always accessible in result processing
        discovered_commands: list = []
        jsonrpc_skills: list = []
        peer_jid: str = (active.get("account") or "").strip()
        a2a_mgr = None
        is_remote: bool = self.parent.is_current_agent_remote()

        try:
            tool_prompt = (get_prompt_by_title("__tool_check_before_review__") or "").strip()
            logger.info("[XMPP-A2A][DIAG] tool_check_review: prompt_template loaded len=%d", len(tool_prompt))
            if not tool_prompt:
                logger.warning("Tool check prompt __tool_check_before_review__ not found, skipping")
                # Fall through to re-dispatch
            else:
                # Optionally fetch peer agent card and inject into context
                agent_card_section = ""
                agent_card_enabled = bool(getattr(self.parent, "agent_card_before_review_enabled", False))
                logger.info("[XMPP-A2A][DIAG] tool_check_review: agent_card_before_review_enabled=%s", agent_card_enabled)
                # Discovery gating: always discover for remote agents (whitelist is security-critical)
                should_discover = agent_card_enabled or is_remote
                if should_discover:
                    logger.info("[XMPP-A2A] tool_check_review: fetching peer agent card before review")
                    try:
                        import time as _diag_time
                        _t_fetch = _diag_time.monotonic()
                        card_json = await self._fetch_peer_agent_card()
                        logger.info("[XMPP-A2A][DIAG] tool_check_review: _fetch_peer_agent_card returned len=%d elapsed=%.2fs", len(card_json or ""), _diag_time.monotonic() - _t_fetch)
                        # Optionally render the agent card section
                        if card_json:
                            agent_card_section = (
                                "\n--- Peer Agent Card ---\n"
                                + card_json
                                + "\n--- End Peer Agent Card ---\n"
                            )
                            logger.info("[XMPP-A2A] tool_check_review: peer agent card fetched (%d chars)", len(card_json))
                        else:
                            logger.info("[XMPP-A2A] tool_check_review: no peer agent card available")

                        # Discover peer ad-hoc commands even if agent card is unavailable
                        try:
                            if peer_jid and "@" in peer_jid:
                                from runtime.apps.sns.xmpp_client import XMPPClientManager
                                client = XMPPClientManager.get_instance().get_client()
                                if client and client.is_client_connected():
                                    a2a_mgr = getattr(client, "_a2a_manager", None)
                                    if a2a_mgr is not None:
                                        card_dict = json.loads(card_json) if card_json else None
                                        discovered_commands = await a2a_mgr.discover_peer_adhoc_commands(
                                            peer_jid, agent_card=card_dict
                                        )
                        except Exception as disc_err:
                            logger.info("[XMPP-A2A][DIAG] tool_check_review: command discovery failed: %s", disc_err, exc_info=True)

                        logger.info("[XMPP-A2A][DIAG] tool_check_review: discovered_commands count=%d nodes=%s", len(discovered_commands), [c.get("node") for c in discovered_commands])

                        # Extract jsonrpc skills from agent card for remote hybrid channel
                        try:
                            card_dict_for_skills = json.loads(card_json) if card_json else {}
                            jsonrpc_skills = [
                                s for s in (card_dict_for_skills.get("skills") or [])
                                if isinstance(s, dict) and str(s.get("transport", "")).lower() == "http_jsonrpc"
                            ]
                        except Exception:
                            jsonrpc_skills = []
                        if jsonrpc_skills:
                            logger.info("[A2A-JSONRPC][DIAG] tool_check_review: found %d jsonrpc skills in card", len(jsonrpc_skills))

                        # Inspect each discovered command's form schema so the LLM
                        # knows exactly which fields are required/optional.
                        try:
                            if discovered_commands and peer_jid and a2a_mgr is not None:
                                await self._inspect_command_forms(a2a_mgr, peer_jid, discovered_commands)
                        except Exception as insp_err:
                            logger.info("[XMPP-A2A][DIAG] tool_check_review: command form inspection failed: %s", insp_err, exc_info=True)

                        # Build A2A tool guidance; inject whether or not card_json exists
                        a2a_tool_section = self._build_a2a_tool_guidance(card_json or "", discovered_commands)
                        logger.info("[XMPP-A2A][DIAG] tool_check_review: a2a_tool_section_len=%d", len(a2a_tool_section or ""))
                        if a2a_tool_section:
                            if agent_card_section:
                                agent_card_section += a2a_tool_section
                            else:
                                agent_card_section = a2a_tool_section
                            logger.info("[XMPP-A2A] tool_check_review: A2A tool guidance injected into prompt")
                    except Exception as ac_err:
                        logger.warning("[XMPP-A2A] tool_check_review: failed during discovery/prompt preparation: %s", ac_err, exc_info=True)

                context_parts = [
                    tool_prompt,
                ]
                if agent_card_section:
                    context_parts.append(agent_card_section)
                context_parts.extend([
                    "\n--- Conversation History ---",
                    talk_history_str or "(empty)",
                ])

                if is_remote:
                    # Remote agent: append task-oriented instructions; do not use local tools
                    remote_instr = (get_prompt_by_title("__remote_agent_tool_check_review__") or "").strip()
                    if not remote_instr:
                        remote_instr = (
                            "--- Instructions for Remote Agent ---\n"
                            "Review the conversation above. If you have tools that can enrich "
                            "your analysis (e.g., lookup, search, query), use them and return the result.\n"
                            "If no tool call is needed, respond with NO_TOOL_NEEDED."
                        )
                    context_parts.append("\n" + remote_instr)

                    # Hybrid mode: tell remote agent how to request local ad-hoc execution
                    if discovered_commands:
                        context_parts.append(
                            "\n--- Remote Agent: How to request ad-hoc command execution ---\n"
                            "You may use your own tools and return their results normally.\n"
                            "If you ALSO need the local XMPP system to invoke a discovered ad-hoc command,\n"
                            "include a JSON block (fenced or inline) in your response:\n"
                            '\n'
                            '  {"a2a_call": {"peer_jid": "<jid>", "command_node": "<node>", "form_data": {...}}}\n'
                            '\n'
                            'For multiple calls:\n'
                            '  {"a2a_calls": [...]}\n'
                            '\n'
                            'Rules:\n'
                            '- Only use peer_jid and command_node values from the Discovered commands section.\n'
                            '- Keep your own tool results in the same response; do NOT remove them.\n'
                            '- The local system will execute and merge the ad-hoc result with your response.\n'
                            '- If no ad-hoc call is needed, do NOT include a JSON block.'
                        )

                    # Hybrid mode: tell remote agent how to request local JSON-RPC execution
                    if jsonrpc_skills:
                        skill_lines = []
                        for sk in jsonrpc_skills:
                            sid = sk.get("id", "")
                            ep = sk.get("endpoint", "")
                            meth = sk.get("method", "")
                            desc = (sk.get("description") or "").strip()
                            skill_lines.append(f'  - id="{sid}" endpoint="{ep}" method="{meth}"')
                            if desc:
                                skill_lines.append(f'      description: {desc[:200]}')
                            ps = sk.get("params_schema")
                            if isinstance(ps, dict) and ps:
                                try:
                                    skill_lines.append("      params_schema: " + json.dumps(ps, ensure_ascii=False))
                                except Exception:
                                    pass
                        context_parts.append(
                            "\n--- Remote Agent: How to request JSON-RPC service invocation ---\n"
                            "If you need the local system to invoke a peer's HTTP JSON-RPC service,\n"
                            "include a JSON block (fenced or inline) in your response:\n"
                            '\n'
                            '  {"jsonrpc_call": {"endpoint": "<endpoint>", "method": "<method>", "params": {...}}}\n'
                            '\n'
                            'For multiple calls:\n'
                            '  {"jsonrpc_calls": [...]}\n'
                            '\n'
                            'Available JSON-RPC skills:\n'
                            + "\n".join(skill_lines) + "\n"
                            '\n'
                            'Rules:\n'
                            '- Only use endpoint and method values from the Available JSON-RPC skills above.\n'
                            '- Fill params according to the skill\'s params_schema.\n'
                            '- Keep your own tool results in the same response; do NOT remove them.\n'
                            '- The local system will execute and merge the JSON-RPC result with your response.\n'
                            '- If no JSON-RPC call is needed, do NOT include a jsonrpc_call JSON block.'
                        )

                question = "\n".join(context_parts)
                logger.info(
                    "[XMPP-A2A][DIAG] tool_check_review: FINAL question (len=%d, is_remote=%s):\n=== BEGIN QUESTION ===\n%s\n=== END QUESTION ===",
                    len(question), is_remote, question,
                )
                self.show_status_on_map("using-tool")
                self.js_task_manager.show_information(lt(
                    "<b>✨Message Received.Using tools before reply.</b>",
                    "<b>✨Message Received.Using tools before reply.</b>",
                ))

                logger.info("[XMPP-A2A][DIAG] tool_check_review: calling chat_with_agent (use_tools=%s)...", not is_remote)
                import time as _diag_time2
                _t_chat = _diag_time2.monotonic()
                tool_result = await self.parent.chat_with_agent(
                    question,
                    conversation_suffix="tool_check_review",
                    use_tools=(not is_remote),
                    use_memory=False,
                    use_knowledge_base=False,
                )
                logger.info(
                    "[XMPP-A2A][DIAG] tool_check_review: chat_with_agent returned elapsed=%.2fs result_len=%d",
                    _diag_time2.monotonic() - _t_chat, len(tool_result or ""),
                )
                self.show_status_on_map("talking")

                tool_result = (tool_result or "").strip()
                logger.info("[XMPP-A2A][DIAG] tool_check_review: raw_tool_result[:500]=%r", tool_result[:500] if tool_result else "")

                # Hybrid merge: remote agent may embed a2a_call / jsonrpc_call JSON alongside its own tool results
                adhoc_text = None
                jsonrpc_text = None
                remote_text = tool_result
                if is_remote and tool_result and discovered_commands and a2a_mgr and peer_jid:
                    try:
                        adhoc_text, remote_text = await self._execute_remote_a2a_requests(
                            remote_text, a2a_mgr, peer_jid, discovered_commands,
                        )
                    except Exception as hybrid_err:
                        logger.warning("[XMPP-A2A] tool_check_review: remote a2a execution failed: %s", hybrid_err, exc_info=True)
                if is_remote and remote_text and jsonrpc_skills:
                    try:
                        jsonrpc_text, remote_text = await self._execute_remote_jsonrpc_requests(
                            remote_text,
                        )
                    except Exception as jsonrpc_err:
                        logger.warning("[A2A-JSONRPC] tool_check_review: remote jsonrpc execution failed: %s", jsonrpc_err, exc_info=True)

                # Merge remote text, local ad-hoc result, and local jsonrpc result
                merge_parts = [p for p in (remote_text, adhoc_text, jsonrpc_text) if p]
                tool_result = "\n\n".join(merge_parts) if merge_parts else remote_text

                # Determine if result is useful.
                # If local ad-hoc was executed, always treat as useful even when
                # remote_text says NO_TOOL_NEEDED. Plain remote errors are not
                # useful and must not be injected into the review history.
                result_upper = (tool_result or "").upper()
                result_lower = (tool_result or "").lower()
                error_markers = (
                    "error:",
                    "tool execution error:",
                    "remote agent network error",
                    "all connection attempts failed",
                    "exception:",
                    "traceback",
                )
                is_plain_error = bool(tool_result) and any(
                    marker in result_lower[:500]
                    for marker in error_markers
                )
                has_useful_result = bool(adhoc_text) or bool(jsonrpc_text) or (
                    bool(tool_result)
                    and "NO_TOOL_NEEDED" not in result_upper
                    and not is_plain_error
                )
                if has_useful_result:
                    logger.info("[XMPP-A2A] tool_check_review: tool returned useful result (%d chars, adhoc=%s)", len(tool_result), bool(adhoc_text))
                    tool_context = tool_result
                elif is_plain_error:
                    logger.info("[XMPP-A2A] tool_check_review: tool check returned a non-useful error, skipping injection")
                else:
                    logger.info("[XMPP-A2A] tool_check_review: no tool invocation needed")
        except Exception as e:
            logger.warning("Tool check before review failed: %s", e, exc_info=True)

        # Re-dispatch conversation_message_received with _tool_check_done=True
        enriched_history = talk_history_str
        if tool_context:
            enriched_history = (
                f"{talk_history_str}\n\n"
                f"[Tool Check Result Before Review]\n{tool_context}"
            )
        logger.info("[XMPP-A2A][DIAG] tool_check_review: EXIT, re-dispatching review with tool_context_len=%d enriched_len=%d", len(tool_context or ""), len(enriched_history or ""))
        asyncio.create_task(self.process_task(
            event="conversation_message_received",
            talk_history_str=enriched_history,
            _tool_check_done=True,
        ))

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

        if len(self.process_info_list) <= 11:
            return

        self._process_info_compacting = True
        try:
            tail_keep = 10
            max_items = 40
            if len(self.process_info_list) <= tail_keep + 1:
                return

            head = list(self.process_info_list[:-tail_keep])
            items_to_summarize = list(head[:max_items])
            remaining = list(head[len(items_to_summarize):])
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

            tail = list(self.process_info_list[-tail_keep:])
            self.process_info_list = [f"Summary: {summary}"] + remaining + tail
            logger.info(
                "Compacted process_info_list. summary_len=%s tail_len=%s",
                len(summary),
                len(tail),
            )

            # Memory capture: save reflection memory for process log compaction summary
            try:
                from runtime.apps.sns.memory.memory_config import MemoryConfig
                from runtime.apps.sns.memory.memory_types import MemoryType
                mm = getattr(self.parent, "memory_manager", None)
                if mm and MemoryConfig.ENABLED:
                    mm.capture_async(
                        MemoryType.REFLECTION,
                        key="Process log compaction summary",
                        content=summary[:500],
                        metadata={"source": "process_info_compact"},
                        importance=60,
                    )
            except Exception as _mem_err:
                logger.warning("Memory capture failed for process log compaction: %s", _mem_err)
        finally:
            self._process_info_compacting = False

    @staticmethod
    def _extract_goal_sections(text: str) -> (str, str):
        raw = (text or "").strip()
        if not raw:
            return "", ""

        stop_section_patterns = [
            r"^\s*#{1,6}\s+.+$",  # Any markdown heading
            r"^\s*Changes Made\b.*$",
            r"^\s*Reasoning\b.*$",
            r"^\s*Next Recommended Actions\b.*$",
        ]

        def _prune_at_extra_sections(section_text: str) -> str:
            if not section_text:
                return ""
            out_lines = []
            for ln in (section_text or "").splitlines():
                if any(re.match(p, ln, flags=re.IGNORECASE) for p in stop_section_patterns):
                    break
                out_lines.append(ln)
            return "\n".join(out_lines).strip()

        parsed = robust_json_loads(raw)
        if isinstance(parsed, dict):
            long_val = (
                parsed.get("Long-Term Goals")
                or parsed.get("Long Term Goals")
                or parsed.get("Long-Term Goal")
                or parsed.get("Long Term Goal")
                or parsed.get("long_term_goals")
                or parsed.get("longTermGoals")
                or parsed.get("long_term_goal")
                or parsed.get("longTermGoal")
                or ""
            )
            short_val = (
                parsed.get("Short-Term Goals")
                or parsed.get("Short Term Goals")
                or parsed.get("Short-Term Goal")
                or parsed.get("Short Term Goal")
                or parsed.get("short_term_goals")
                or parsed.get("shortTermGoals")
                or parsed.get("short_term_goal")
                or parsed.get("shortTermGoal")
                or ""
            )
            long_txt = "\n".join(long_val) if isinstance(long_val, list) else str(long_val or "")
            short_txt = "\n".join(short_val) if isinstance(short_val, list) else str(short_val or "")
            return (_prune_at_extra_sections(long_txt.strip()), _prune_at_extra_sections(short_txt.strip()))

        def _find_header_idx(lines, label_patterns):
            for i, ln in enumerate(lines):
                for pat in label_patterns:
                    if re.match(pat, ln, flags=re.IGNORECASE):
                        return i
            return None

        lines = [ln.rstrip() for ln in raw.splitlines()]
        long_header = _find_header_idx(
            lines,
            [
                r"^\s*(#+\s*)?Long[- ]Term Goals\s*:?\s*$",
                r"^\s*(#+\s*)?Long[- ]Term Goal\s*:?\s*$",
            ],
        )
        short_header = _find_header_idx(
            lines,
            [
                r"^\s*(#+\s*)?Short[- ]Term Goals\s*:?\s*$",
                r"^\s*(#+\s*)?Short[- ]Term Goal\s*:?\s*$",
            ],
        )

        if long_header is None and short_header is None:
            return "", ""

        def _slice_section(start_idx, stop_idx):
            if start_idx is None:
                return ""
            body_start = start_idx + 1
            body_end = stop_idx if stop_idx is not None else len(lines)
            collected = []
            for ln in lines[body_start:body_end]:
                if any(re.match(p, ln, flags=re.IGNORECASE) for p in stop_section_patterns):
                    break
                collected.append(ln)
            section = "\n".join(collected).strip()
            return _prune_at_extra_sections(section)

        if long_header is not None and short_header is not None:
            if long_header < short_header:
                return _slice_section(long_header, short_header), _slice_section(short_header, None)
            return _slice_section(long_header, None), _slice_section(short_header, long_header)

        return _slice_section(long_header, None), _slice_section(short_header, None)

    async def _summarize_process_and_update_goals(self):
        if self._process_plan_summarizing:
            return

        self._process_plan_summarizing = True
        self._process_plan_summary_due = False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._process_plan_summarizing = False
            return

        loop.create_task(self.process_task(action="process_plan_summary"))

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
