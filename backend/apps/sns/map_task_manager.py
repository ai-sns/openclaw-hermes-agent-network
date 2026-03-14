import json
import asyncio
from db.DBFactory import query_single_map_task, update_map_task
from db.DBFactory import get_prompt_by_title, upsert_prompt_by_title
from i18n import lt
from typing import Dict, Any, Optional
from util import generate_random_id
import logging
from backend.shared.utils import robust_json_loads
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
        self._process_plan_summarizing = False
        self._process_info_since_compact = 0
        self._process_info_since_plan_summary = 0

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

        self._process_info_since_compact += 1
        self._process_info_since_plan_summary += 1

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

        self._process_info_since_plan_summary = 0

        try:
            loop = asyncio.get_running_loop()
            logger.info(
                "Scheduling process plan summary (every_n=%s, process_info_len=%s)",
                summary_every,
                len(getattr(self, "process_info_list", []) or []),
            )
            loop.create_task(self._summarize_process_and_update_goals())
        except RuntimeError:
            return

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
                from backend.apps.sns.memory.memory_config import MemoryConfig
                from backend.apps.sns.memory.memory_types import MemoryType
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
                or parsed.get("长期目标")
                or parsed.get("长期目标列表")
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
                or parsed.get("短期目标")
                or parsed.get("短期目标列表")
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
                r"^\s*(#+\s*)?长期目标\s*[:：]?\s*$",
            ],
        )
        short_header = _find_header_idx(
            lines,
            [
                r"^\s*(#+\s*)?Short[- ]Term Goals\s*:?\s*$",
                r"^\s*(#+\s*)?Short[- ]Term Goal\s*:?\s*$",
                r"^\s*(#+\s*)?短期目标\s*[:：]?\s*$",
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
        try:
            logger.info(
                "Process plan summary start (process_info_len=%s)",
                len(getattr(self, "process_info_list", []) or []),
            )
            plan_manage_prompt = (get_prompt_by_title("__plan_manage__") or "").strip()
            current_goals = (get_prompt_by_title("__plan_goals__") or "").strip()
            current_long_goals, current_short_goals = self._extract_goal_sections(current_goals)
            process_log = "\n".join(
                f"{idx + 1}. {item}" for idx, item in enumerate(list(self.process_info_list))
            )

            msg_parts = []
            if plan_manage_prompt:
                msg_parts.append(plan_manage_prompt)
            msg_parts.append("Current Long-Term Goals (may be empty):")
            msg_parts.append((current_long_goals or "").strip() or "(empty)")
            msg_parts.append("Current Short-Term Goals (may be empty):")
            msg_parts.append((current_short_goals or "").strip() or "(empty)")
            msg_parts.append("Process log entries:")
            msg_parts.append(process_log)
            msg_parts.append(
                "\nOutput requirements:\n"
                "- Provide updated goals only.\n"
                "- Include BOTH sections with these exact labels:\n"
                "  Long-Term Goals:\n"
                "  Short-Term Goals:\n"
                "- Do NOT include any other sections such as Changes Made/Reasoning/Next Recommended Actions.\n"
            )

            prompt = "\n\n".join([p for p in msg_parts if p is not None])

            result = ""
            try:
                result = await self.parent.chat_with_agent(
                    prompt,
                    conversation_suffix="process_plan_manage",
                    use_tools=False,
                    use_memory=False,
                    use_knowledge_base=False,
                )
            except Exception as e:
                logger.warning("Failed to call agent for process plan summary: %s", e)
                result = ""

            long_goals, short_goals = self._extract_goal_sections((result or "").strip())
            if not long_goals and not short_goals:
                logger.warning(
                    "Plan summary did not contain goal sections; skipping __plan_goals__ update. raw_result_head=%s",
                    (result or "")[:300],
                )
                return

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
        finally:
            self._process_plan_summarizing = False

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
