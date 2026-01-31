import json
import asyncio
from db.DBFactory import query_single_map_task,update_map_task
from i18n import lt
from typing import  Dict, Any, Optional
from util import generate_random_id
import logging
logger = logging.getLogger(__name__)

class MapTaskManager:
    def __init__(self,parent):
    # def __init__(self, parent:MessageBox):
        # 初始化一个字典和几个列表
        self.parent = parent
        self.js_task_manager = None
        self.message_dict = {}
        self.specified_context_message_list = []
        self.specify_context_message_flag = False
        self.kwargs = {}
        self.init_flag = False
        self.last_param = {}
        self.current_activity_objective = ""
        self.current_objective = ""
        self.current_task_record = None
        self.main_task = ""
        self.sub_task_list=[]
        self.current_sub_task=None
        self.current_sub_task_index = 0
        self.process_info_list = []
        self.process_list = []
        self.current_process = None


        self.current_situation = ""
        self.reviewing_current_process = False
        self.reviewing_task = False


        self.init_task_mng()

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

        self.js_task_manager = self.parent.taskmng_js
        self.current_task_record = query_single_map_task(status=1)
        if self.current_task_record:
            self.main_task = self.current_task_record.detail


        self.current_objective = ""
        self.init_flag =True

    def re_init(self):
        # 清空字典和列表，重置标志
        self.message_dict.clear()
        self.specified_context_message_list.clear()
        self.specify_context_message_flag = False


    def get_sub_task_list(self):
        if not self.current_task_record.sub_task_list:
            result = [""]
        else:
            result = json.loads(self.current_task_record.sub_task_list)
            self.sub_task_list = result["tasks"]  # 保存到全局变量
        return result

    def get_current_sub_task_str(self):
        result = self.current_task_record.current_sub_task
        return result

    def get_current_sub_task(self):
        result = self.current_task_record.current_sub_task
        self.current_sub_task = json.loads(result)  # 保存到全局变量
        return self.current_sub_task

    def set_sub_task_completed(self):
        self.add_process_info_to_list(f"The follow sub task is completed:{json.dumps(self.current_sub_task, indent=4, ensure_ascii=False)}\n")
        # self.parent.write_thinking_process_to_pane("##The current sub task is completed:" + json.dumps(self.current_sub_task, indent=4, ensure_ascii=False))
        self.update_task_plan_in_pane(self.current_sub_task_index)
        self.current_sub_task_index = self.current_sub_task_index + 1

        if self.current_sub_task_index < len(self.sub_task_list):
            self.current_sub_task = self.sub_task_list[self.current_sub_task_index]
            update_map_task(self.current_task_record.id, current_sub_task=json.dumps(self.current_sub_task, indent=4, ensure_ascii=False))
            self.reload_current_task_record()
        else:
            print("all task is completed")

    def get_task_summary(self):
        main_task = self.main_task
        sub_task_list_str = json.dumps(self.get_sub_task_list(), indent=4, ensure_ascii=False)
        current_sub_task_str =  json.dumps(self.get_current_sub_task(), indent=4, ensure_ascii=False)
        # 通过换行符将处理信息列表连接成一个字符串
        # 为处理信息列表中的每个项添加序号
        process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.process_info_list))
        command_status = self.parent.command_status
        result = f"""### 任务说明
#### **背景**
我正在参加一个基于Google地图的虚拟社交游戏。玩家需要扮演角色在虚拟地图上探索、社交并完成任务。

#### **主任务**
{main_task}

#### **子任务**
- 子任务列表
{sub_task_list_str}
- 当前子任务
{current_sub_task_str}
---

#### **任务执行过程记录**
{process_info_list_str}

---
        """
        return result

    def get_task_summary_simple(self):
        main_task = self.main_task
        sub_task_list_str = json.dumps(self.get_sub_task_list(), indent=4, ensure_ascii=False)
        current_sub_task_str = json.dumps(self.get_current_sub_task(), indent=4, ensure_ascii=False)
        # 通过换行符将处理信息列表连接成一个字符串
        # 为处理信息列表中的每个项添加序号
        process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.process_info_list))
        command_status = self.parent.command_status
        result = f"""### 任务说明
#### **背景**
我正在参加一个基于Google地图的虚拟社交游戏。玩家需要扮演角色在虚拟地图上探索、社交并完成任务。

#### **任务**
{main_task}

#### **任务执行过程记录**
{process_info_list_str}

---
        """
        return result

    def get_current_objective(self):
        objective=self.current_objective
        return objective

    def get_current_activity_objective(self):
        objective = self.current_activity_objective
        return objective

    def add_process(self, **kwargs) -> str:
        """添加一个新的进程到 process_list，并更新 current_process。"""
        new_process = {
            "id": generate_random_id(),
            "current_place": kwargs.get("current_place",""),
            "current_position": kwargs.get("current_position",[]),
            "tool_used_count": kwargs.get("tool_used_count", 0),
            "people_communicated_count": kwargs.get("people_communicated_count", 0),
            "people_communicated_list": kwargs.get("people_communicated_list", []),
            "rounds_current_person": kwargs.get("rounds_current_person", 0),
            "ability_used_list": kwargs.get("ability_used_list",[]),
            "process_info_list": kwargs.get("process_info_list", []),
            "process_objective": kwargs.get("process_objective", "")

        }

        self.process_list.append(new_process)
        self.current_process = new_process  # 更新 current_process 到新添加的进程
        self.parent.ability_list[2]["status"] = "enabled"
        self.parent.ability_list[0]["status"] = "enabled"

        return new_process

    def update_process(self, process_id: str, **kwargs) -> bool:
        """更新指定ID的进程信息，并可能更新 current_process。"""
        for process in self.process_list:
            if process["id"] == process_id:
                process.update(kwargs)  # 使用 update 方法更新字典
                self.current_process = process  # 更新 current_process 为最新的进程
                return True
        return False  # 如果找不到进程ID，返回 False

    def get_process(self, process_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取进程信息。"""
        for process in self.process_list:
            if process["id"] == process_id:
                self.current_process = process  # 如果找到进程，更新 current_process
                return process
        return None  # 如果找不到进程ID，返回 None

    def get_current_process(self):
        process = self.current_process
        current_place = self.parent.get_current_place()
        current_position = self.parent.get_current_position()
        process_target=self.current_objective if self.current_objective else  self.get_current_sub_task()["details"]

        if not process:
           process = self.add_process(current_place=current_place,current_position=current_position,process_target=process_target)
        else:
            if process.get("current_place")!=current_place:
                process = self.add_process(current_place=current_place, current_position=current_position, process_target=process_target)

        return process

    def update_current_process(self):
        pass

    def review_current_process(self):
        pass

    def review_task(self):
        self.reviewing_task = True
        asyncio.create_task(self.parent.ask_agent_to_update_task())


    def exception_detect_tool(self):
        process_info = self.current_process
        # self.parent.write_thinking_process_to_pane("in exception_detect_tool\n")
        # self.parent.write_thinking_process_to_pane(json.dumps(process_info, indent=4, ensure_ascii=False))
        # self.parent.write_thinking_process_to_pane(f"self.parent.min_place_move_score:{self.parent.min_place_move_score}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_people_comm:{self.parent.max_people_comm}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_tool_usage:{self.parent.max_tool_usage}\n")
        current_process = self.get_current_process()
        tool_used_count = current_process.get("tool_used_count", 0)  # Default to 0 if not found
        people_communicated_count = current_process.get("people_communicated_count", 0)  # Default to 0 if not found
        last_ability = current_process["ability_used_list"][-1] if current_process["ability_used_list"] else ""

        # Condition: Tool usage has reached or exceeded the maximum limit
        if tool_used_count >= self.parent.max_tool_usage:
            if people_communicated_count >= self.parent.max_people_comm:
                objective_to_achieve = self.current_objective if self.current_objective else self.current_sub_task["details"]
                provided_place_list = json.dumps(self.parent.get_place_list(), indent=4, ensure_ascii=False)
                self.parent.ask_agent_to_pick_place_list_sync(objective_to_achieve, provided_place_list)
            else:
                self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
                self.set_command_status("ask_agent_to_pick_people_list")
                provided_profile_list = json.dumps(self.parent.get_people_list(), indent=4, ensure_ascii=False)
                self.current_process["ability_used_list"].append("activity_find_people_from_list_to_talk")
                self.current_process["people_communicated_count"] = self.current_process.get("people_communicated_count", 0) + 1
                self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)
            return  # Exit early as further checks are unnecessary

        # Condition: Tool usage is at least half of the maximum limit
        if tool_used_count >= self.parent.max_tool_usage / 2:
            if last_ability == "activity_find_tool_from_list_to_use":
                if people_communicated_count < self.parent.max_people_comm:
                    self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
                    self.set_command_status("ask_agent_to_pick_people_list")
                    provided_profile_list = json.dumps(self.parent.get_people_list(), indent=4, ensure_ascii=False)
                    self.current_process["ability_used_list"].append("activity_find_people_from_list_to_talk")
                    self.current_process["people_communicated_count"] = self.current_process.get("people_communicated_count", 0) + 1
                    self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)
                    return  # Exit early as further checks are unnecessary

        # Default action: Ask the agent to pick a tool


        self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
        self.set_command_status("ask_agent_to_pick_a_tool")
        task_summary = self.get_task_summary()

        provided_tool_list = self.parent.get_tool_list()
        self.current_process["ability_used_list"].append("activity_find_tool_from_list_to_use")
        self.current_process["tool_used_count"] = self.current_process.get("tool_used_count", 0) + 1
        self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list, indent=4, ensure_ascii=False))



    def exception_detect_people(self):
        process_info = self.current_process
        # self.parent.write_thinking_process_to_pane("in exception_detect_people\n")
        # self.parent.write_thinking_process_to_pane(json.dumps(process_info, indent=4, ensure_ascii=False))
        # self.parent.write_thinking_process_to_pane(f"self.parent.min_place_move_score:{self.parent.min_place_move_score}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_people_comm:{self.parent.max_people_comm}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_tool_usage:{self.parent.max_tool_usage}\n")
        current_process = self.get_current_process()
        people_communicated_count = current_process.get("people_communicated_count", 0)  # Default to 0 if not present
        tool_used_count = current_process.get("tool_used_count", 0)  # Default to 0 if not present
        last_ability = current_process["ability_used_list"][-1] if current_process["ability_used_list"] else ""

        # Condition: Communication with people has reached or exceeded the maximum limit
        if people_communicated_count >= self.parent.max_people_comm:
            if tool_used_count >= self.parent.max_tool_usage:
                objective_to_achieve = self.current_objective if self.current_objective else self.current_sub_task["details"]
                provided_place_list = json.dumps(self.parent.get_place_list(), indent=4, ensure_ascii=False)
                self.parent.ask_agent_to_pick_place_list_sync(objective_to_achieve, provided_place_list)
            else:
                self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
                self.set_command_status("ask_agent_to_pick_a_tool")
                task_summary = self.get_task_summary()

                provided_tool_list = self.parent.get_tool_list()
                self.current_process["ability_used_list"].append("activity_find_tool_from_list_to_use")
                self.current_process["tool_used_count"] = self.current_process.get("tool_used_count", 0) + 1
                self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list, indent=4, ensure_ascii=False))
            return  # Exit early as further checks are unnecessary

        # Condition: Communication is at least half of the maximum limit
        if people_communicated_count >= self.parent.max_people_comm / 2:
            if last_ability == "activity_find_people_from_list_to_talk":
                if tool_used_count < self.parent.max_tool_usage:
                    self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
                    self.set_command_status("ask_agent_to_pick_a_tool")
                    task_summary = self.get_task_summary()

                    provided_tool_list = self.parent.get_tool_list()
                    self.current_process["ability_used_list"].append("activity_find_tool_from_list_to_use")
                    self.current_process["tool_used_count"] = self.current_process.get("tool_used_count", 0) + 1
                    self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list, indent=4, ensure_ascii=False))
                    return  # Exit early as further checks are unnecessary

        # Default action: Ask the agent to pick people to communicate with


        self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
        self.set_command_status("ask_agent_to_pick_people_list")
        provided_profile_list = json.dumps(self.parent.get_people_list(), indent=4, ensure_ascii=False)
        self.current_process["ability_used_list"].append("activity_find_people_from_list_to_talk")
        self.current_process["people_communicated_count"] = self.current_process.get("people_communicated_count", 0) + 1
        self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)

    def exception_detect_place(self,target_position,target_score,target_place):
        process_info = self.current_process
        # self.parent.write_thinking_process_to_pane("in exception_detect_place\n")
        # self.parent.write_thinking_process_to_pane(json.dumps(process_info, indent=4, ensure_ascii=False))
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_place_arrived:{self.parent.max_place_arrived}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.min_place_move_score:{self.parent.min_place_move_score}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_people_comm:{self.parent.max_people_comm}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.max_tool_usage:{self.parent.max_tool_usage}\n")
        # self.parent.write_thinking_process_to_pane(f"self.parent.place_arrived_count:{json.dumps( self.parent.place_arrived_count, indent=4, ensure_ascii=False)}\n")

        max_place_arrived=self.parent.max_place_arrived
        current_process = self.get_current_process()
        current_position = self.parent.get_current_position()
        people_communicated_count = current_process.get("people_communicated_count", 0)  # Default to 0 if not present
        tool_used_count = current_process.get("tool_used_count", 0)  # Default to 0 if not present
        last_ability = current_process["ability_used_list"][-1] if current_process["ability_used_list"] else ""
        target_position_str = f"{target_position[0]}_{target_position[1]}"
        target_place_arrived_count = self.parent.place_arrived_count.get(target_position_str,0)

        if target_place_arrived_count < max_place_arrived:
            if current_position != target_position:
                min_place_move_score = self.parent.min_place_move_score
                if target_score >= min_place_move_score:
                    self.parent.place_arrived_count[target_position_str] = target_place_arrived_count + 1
                    self.parent.current_place=target_place
                    self.parent.current_position = target_position
                    self.add_process(current_place=self.parent.current_place, current_position=self.parent.current_position)
                    self.parent.move_to_a_place(target_position[0],target_position[1])
                    return

        if last_ability == "activity_find_tool_from_list_to_use":
            if people_communicated_count >= self.parent.max_people_comm:
                if tool_used_count >= self.parent.max_tool_usage:
                    self.parent.place_arrived_count[target_position_str] = 0
                    self.parent.explore_the_map()
                else:
                    self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
                    self.set_command_status("ask_agent_to_pick_a_tool")
                    task_summary = self.get_task_summary()

                    provided_tool_list = self.parent.get_tool_list()
                    self.current_process["ability_used_list"].append("activity_find_tool_from_list_to_use")
                    self.current_process["tool_used_count"] = self.current_process.get("tool_used_count", 0) + 1
                    self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list, indent=4, ensure_ascii=False))
            else:
                self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
                self.set_command_status("ask_agent_to_pick_people_list")
                provided_profile_list = json.dumps(self.parent.get_people_list(), indent=4, ensure_ascii=False)
                self.current_process["ability_used_list"].append("activity_find_people_from_list_to_talk")
                self.current_process["people_communicated_count"] = self.current_process.get("people_communicated_count", 0) + 1
                self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)
        elif last_ability == "activity_find_people_from_list_to_talk" or last_ability=="":
            if tool_used_count >= self.parent.max_tool_usage:
                if people_communicated_count >= self.parent.max_people_comm:
                    self.parent.place_arrived_count[target_position_str] = 0
                    self.parent.explore_the_map()
                else:
                    self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
                    self.set_command_status("ask_agent_to_pick_people_list")
                    provided_profile_list = json.dumps(self.parent.get_people_list(), indent=4, ensure_ascii=False)
                    self.current_process["ability_used_list"].append("activity_find_people_from_list_to_talk")
                    self.current_process["people_communicated_count"] = self.current_process.get("people_communicated_count", 0) + 1
                    self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)
            else:
                self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
                self.set_command_status("ask_agent_to_pick_a_tool")
                task_summary = self.get_task_summary()

                provided_tool_list = self.parent.get_tool_list()
                self.current_process["ability_used_list"].append("activity_find_tool_from_list_to_use")
                self.current_process["tool_used_count"] = self.current_process.get("tool_used_count", 0) + 1
                self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list, indent=4, ensure_ascii=False))





    def update_task_plan_in_pane(self, finished_task_index=-1):

        text_content=self.parent.plan_edit.toPlainText()
        process_list_start = text_content.find("📜【Process history】")
        if process_list_start != -1:
            process_content = text_content[process_list_start:].strip()
        else:
            process_content = "📜【Process history】"

        # 输出提取的内容
        print(process_content)


        self.parent.plan_edit.clear()

        self.parent.write_task_plan_to_pane(process_content)

    def reload_current_task_record(self):
        record = query_single_map_task(id=self.current_task_record.id)
        self.current_task_record = record
        return record


    def process_task(self,**kwargs):
        logger.info("[Step-05],Start process_task...")
        self.pause_and_wait_for_resume()
        self.kwargs = kwargs
        action_requested = kwargs.get("action", "")
        event = kwargs.get("event", "")
        instruction = kwargs.get("instruction", "")

        human_send_flag =  kwargs.get("human_send_flag",False)
        if self.parent.human_take_over:
            if action_requested=="process_activity":
                if not human_send_flag:
                    return

        if self.parent.stopping_ai_process_flag:
            self.parent.stop_AI_process_finished()
            return


        if not self.init_flag:
            self.init_task_mng()




        if action_requested == "plan_task":
            task = kwargs.get("task","")
            self.js_task_manager.show_information(lt("decomposing plan","正在分解计划"))
            self.set_command_status("ask_agent_to_decompose_task")
            asyncio.create_task(self.parent.ask_agent_to_decompose_task(task))

        elif event=="ask_agent_to_decompose_task_returned":
            result = kwargs.get("result", "")
            sub_task_list_str = result
            self.parent.handle_agent_plan_task_result(sub_task_list_str)

        elif event=="task_plan_is_decomposed":
            self.js_task_manager.show_information(lt("task plan is decomposed,ready to start plan step", "计划已分解，准备开始执行任务步骤"))
            self.set_command_status("")
            self.parent.start_task()

        elif action_requested=="process_activity":

            self.parent.write_on_going_process_to_pane(lt("Agent is thinking how to proceed current action.","Agent正在思考如何开展当前行动。"))
            ask_content = kwargs.get("ask_content", self.get_current_objective())
            stop_review = True
            if not self.parent.human_take_over:
                if not stop_review:
                    if not self.reviewing_task:
                        self.review_task()
                        return
                    else:
                        self.reviewing_task=False

            item_to_achieved = ""
            if ask_content:
                item_to_achieved = ask_content

            self.js_task_manager.show_information(lt(f"Agent is thinking how to proceed:{item_to_achieved}", f"Agent正在思考如何进展:{item_to_achieved}"))
            self.set_command_status("ask_agent_instruction_to_process_activity")

            asyncio.create_task(self.parent.ask_agent_instruction_to_process_activity(ask_content))


        elif action_requested=="process_human_instruction":

            ask_content = kwargs.get("ask_content", "")

            self.set_command_status("ask_agent_instruction_to_process_human_instruction")

            asyncio.create_task(self.parent.ask_agent_instruction_to_process_human_instruction(ask_content))


        elif event=="agent_instruction_to_process_activity_returned":
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

            # 使用字典的get方法以安全地获取值，避免KeyError
            function_str = activity_mapping.get(function, 'Unknown function:'+function)

            self.js_task_manager.show_information(lt(f"Agent return instruction:{function_str}.The target is:{objective_to_achieve}", f"Agent返回指令:{function_str}。目标是:{objective_to_achieve}"))
            self.set_command_status("")
            self.parent.parse_agent_instruction_for_process_activity(instruction)


        elif event=="agent_instruction_to_process_human_instruction_returned":
            self.set_command_status("")
            self.parent.parse_agent_instruction_for_process_human_instruction(instruction)


        elif action_requested=="ask_agent_to_pick_people_list":
            self.parent.write_on_going_process_to_pane("Is picking people to talk")
            self.js_task_manager.show_information(lt(f"To pick people from list", f"正从名单中筛选人员"))
            self.set_command_status("ask_agent_to_pick_people_list")
            provided_profile_list = kwargs.get("provided_profile_list", "")
            self.parent.ask_agent_to_pick_people_list_sync(provided_profile_list)

        elif event=="agent_pick_people_list_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = json.loads(result)
            if people_dict:
                nick_name = people_dict["nick_name"]
            else:
                nick_name = ""
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent选择{result}进行交谈"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"]=result
            self.parent.handle_agent_pick_people_list_result(result)
        elif event=="ask_agent_start_to_talk_to_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = json.loads(result)
            if people_dict:
                nick_name = people_dict["nick_name"]
            else:
                nick_name = ""
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent选择{result}进行交谈"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"]=result
            self.parent.handle_ask_agent_start_to_talk_to_a_people_result(result)

        elif event=="ask_agent_start_to_sell_to_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = json.loads(result)
            if people_dict:
                nick_name = people_dict["nick_name"]
            else:
                nick_name = ""
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent选择{result}进行交谈"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"]=result
            self.parent.handle_ask_agent_start_to_sell_to_a_people_result(result)

        elif event=="ask_agent_start_to_buy_from_a_people_returned":
            self.show_status_on_map("talking")
            result = kwargs.get("result", "")
            people_dict = json.loads(result)
            if people_dict:
                nick_name = people_dict["nick_name"]
            else:
                nick_name = ""
            self.parent.write_on_going_process_to_pane(f"Talking with {nick_name}")
            self.js_task_manager.show_information(lt(f"Agent choose {nick_name} to talk", f"Agent选择{result}进行交谈"))
            self.set_command_status("")
            self.last_param = {}
            self.last_param["people_list_picked"]=result
            self.parent.handle_ask_agent_start_to_buy_from_a_people_result(result)


        elif event =="conversation_message_received":
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





        elif action_requested == "request_the_service":

            provided_people_list_str = self.last_param.get("people_list_picked", "")
            self.js_task_manager.show_information(lt(f"Thinking how to talk to the people selected", f"思考如何与选中的人沟通"))
            self.set_command_status("ask_agent_how_to_request_the_service")


        elif event == "ask_agent_how_to_request_the_service_returned":
            result = kwargs.get("result", "")
            self.js_task_manager.show_information(lt(f"Agent tell how to talk:{result}", f"Agent返回如何沟通{result}"))
            self.set_command_status("")
            self.parent.handle_agent_tell_me_how_to_talk_result(result)


        elif event == "agent_pick_place_list_returned":
            self.parent.write_on_going_process_to_pane("Is picking place to move")
            result = kwargs.get("result", "")
            place_dict = json.loads(result)
            if place_dict:
                place_name = place_dict[0]["place_name"]
            else:
                place_name = ""


            self.add_process_info_to_list(lt(f"Select the place: {place_name}\n", f"选择了地点: {place_name}\n"))
            self.js_task_manager.show_information(lt(f"Agent selected place: {place_name}", f"Agent选择了地点: {place_name}"))
            self.set_command_status("")
            self.parent.handle_agent_pick_place_list_result(result)


        elif action_requested == "move_to_a_place":
            self.show_status_on_map("moving")
            self.parent.write_on_going_process_to_pane("Is moving to the place")
            place_name = kwargs.get("place_name", "")
            lng = kwargs.get("lng", 0)
            lat = kwargs.get("lat", 0)
            match_score = int(kwargs.get("match_score",0))



            self.parent.ability_list = [
                {
                    "function_name": "【activity_find_people_from_list_to_talk】",
                    "function_description": "从人员名单中查找合适的人进行沟通，当你需要别人的帮助，需要别人给你指引的时候可以选择该功能，筛选人员不允许分多步骤筛选",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_place_from_list_to_move】",
                    "function_description": "从地点列表中查找合适的地方作为目的地，当你需要去某个地方的时候可以选择该功能，筛选地方不允许分多步骤筛选",
                    "status": "enabled"
                },
                {
                    "function_name": "【activity_find_tool_from_list_to_use】",
                    "function_description": "使用该功能可以从工具列表中查找合适的工具来调用系统服务、使用AI技能，解决其他功能解决不了的问题。筛选工具不允许分多步骤筛选。",
                    "status": "enabled"
                }
            ]
            target_place = place_name
            target_position = [lng,lat]
            target_score = match_score
            self.exception_detect_place(target_position, target_score,target_place)

            #原来没有检测的做法
            # self.js_task_manager.show_information(lt(f"Moving to place: {place_name},position:{lng},{lat}", f"正在移动到地点: {place_name},地理位置是:{lng},{lat}"))
            # self.set_command_status("move_to_a_place")
            # self.parent.move_to_a_place(lng, lat)

        elif event == "arrived_at_place":
            place_name = kwargs.get("place_name", "")
            self.add_process_info_to_list(lt(f"Arrived at place: {place_name}\n", f"已到达地点: {place_name}\n"))
            self.show_status_on_map("watching")
            self.parent.write_task_process_to_pane(lt(f"Arrived at place: {place_name}\n", f"已到达地点: {place_name}\n"))
            self.js_task_manager.show_information(lt(f"Arrived at place: {place_name}", f"已到达地点: {place_name}"))
            self.set_command_status("")
            self.parent.handle_arrived_at_place(place_name)

        elif event=="move_to_a_place_completed":
            # self.parent.write_thinking_process_to_pane(lt(f"Move to a place completed:", f"移动到某个地方已完成"), "map_task_manager.process_task：move_to_a_place_completed")
            self.set_sub_task_completed()
            if self.current_sub_task:
                self.set_command_status("process_activity")
                description = kwargs.get("description", "")
                self.process_task(action="process_activity", ask_content=self.get_current_objective() + description)

        elif action_requested == "find_tool_from_list_to_use":
            self.parent.write_on_going_process_to_pane("Is picking a tool")
            self.js_task_manager.show_information(lt(f"Try to find a tool", f"尝试使用工具"))
            self.set_command_status("ask_agent_to_pick_a_tool")
            task_summary = self.get_task_summary()

            provided_tool_list=self.parent.get_tool_list()

            self.parent.ask_agent_to_pick_a_tool_sync(task_summary, json.dumps(provided_tool_list,indent=4, ensure_ascii=False))

        elif event=="ask_agent_to_pick_a_tool_returned":
            self.show_status_on_map("using-tool")
            self.parent.write_on_going_process_to_pane("Is using tool")
            result = kwargs.get("result", "")
            tool_dict = json.loads(result)
            if tool_dict:
                tool_name = tool_dict[0]["name"]
            else:
                tool_name = ""
            self.js_task_manager.show_information(lt(f"Agent choose the tool:{tool_name}", f"Agent选择了工具：{tool_name}"))
            self.set_command_status("")
            if result:
                result_list = json.loads(result)
                if result_list:
                    self.last_param = {}
                    self.last_param["tool_picked"]=result
                    self.parent.handle_agent_pick_a_tool_result(result)
                    return

            #if no service or skill,explore the map to discover more service of ask people to help
            self.set_command_status("explore_the_map")
            task_summary = kwargs.get("objective_to_achieve", "")
            self.current_objective =task_summary
            self.parent.ask_other_people_for_help(objective_to_achieve=task_summary)

        elif event=="ask_agent_to_pick_a_tool_to_buy_returned":
            result = kwargs.get("result", "")
            tool_dict = json.loads(result)
            if tool_dict:
                tool_name = tool_dict[0]["name"]
            else:
                tool_name = ""
            self.js_task_manager.show_information(lt(f"Agent choose the tool:{tool_name} to buy", f"Agent建议购买工具：{tool_name}"))
            self.set_command_status("")
            if result:
                result_list = json.loads(result)
                if result_list:
                    self.last_param = {}
                    self.last_param["tool_picked"]=result
                    self.parent.handle_agent_pick_a_tool_to_buy_result(result)
                    return


        elif event == "ask_people_help_success":
            if self.parent.command_status == "explore_the_map":
                result = kwargs.get("result", "")
                self.process_task(action="process_activity", ask_content=self.get_current_sub_task_str() + result)



        elif event == "on_moving_completed":
            if self.parent.command_status == "explore_the_map":
                # self.parent.write_thinking_process_to_pane("on_moving_completed","map_task_manager.process_task  on_moving_completed")
                # self.parent.write_thinking_process_to_pane("explore_the_map", "map_task_manager.process_task on_moving_completed")
                provided_service_list = self.parent.get_service_list()
                provided_skill_list = self.parent.get_skill_list()
                if provided_service_list:
                    self.js_task_manager.show_information(lt(f"Try to find a service or skill", f"尝试调用系统服务或使用技能"))
                    self.set_command_status("ask_agent_to_pick_a_tool")
                    task_summary =self.get_current_objective()
                    self.parent.ask_agent_to_pick_a_tool_sync(task_summary, provided_service_list,provided_skill_list)
                else:
                    # if no service or skill,explore the map to discover more service of ask people to help
                    self.set_command_status("explore_the_map")
                    task_summary = kwargs.get("objective_to_achieve", "")
                    self.current_objective = task_summary
                    self.parent.ask_other_people_for_help(objective_to_achieve=task_summary)

        elif event=="skill_executed":
            self.set_sub_task_completed()
            if self.current_sub_task:
                self.set_command_status("process_activity")
                result =kwargs.get("result", "")
                self.process_task(action="process_activity", ask_content=self.get_current_sub_task_str() + result)

        elif action_requested == "explore_the_map":
            self.parent.move_on()

    def set_command_status(self,status):
        self.parent.command_status = status

    def add_process_info_to_list(self,info):
        self.process_info_list.append(info)

    def set_current_objective(self,content):
        self.current_objective = content

    def set_current_activity_objective(self,content):
        self.current_activity_objective = content


    def show_information(self,info,type_str="1"):
        self.js_task_manager.show_information(info,type_str)

    def write_on_going_process_to_pane(self,content):
        self.parent.write_on_going_process_to_pane(content)

    def write_task_process_to_pane(self, content):
        self.parent.write_task_process_to_pane(content)

    def write_thinking_process_to_pane(self, content, function_name=""):
        self.parent.write_thinking_process_to_pane(content,function_name)

    def show_status_on_map(self, status):
        self.parent.show_status_on_map(status)


    def append_message(self, message_id, value):
        """向字典中添加键值对"""
        self.message_dict[message_id] = value
        if self.specify_context_message_flag:
            self.specified_context_message_list.append(message_id)

    def remove_message_by_id(self, message_id):
        if message_id in self.message_dict:
            del self.message_dict[message_id]
        else:
            raise KeyError(f"Message ID '{message_id}' not found in message_dict.")

        self.remove_specified_message_id(message_id)

    def get_messages(self):
        if self.specify_context_message_flag:
            # 根据 specified_context_message_list 中的键获取对应的消息
            messages = [self.message_dict[key] for key in self.specified_context_message_list if key in self.message_dict]
        else:
            # 返回所有消息
            messages = list(self.message_dict.values())
        return messages

    def set_specified_status(self,flag):
        self.specify_context_message_flag = flag
        self.specified_context_message_list.clear()

    def append_specified_message_id(self, message_id):
        """将 message_id 添加到 specified_context_message_list 中（如果它在 message_dict 的键中）"""
        if message_id in self.message_dict:
            if message_id not in self.specified_context_message_list:
                self.specified_context_message_list.append(message_id)
            # 按照 message_dict 中键的顺序排序
            self.specified_context_message_list.sort(key=lambda x: list(self.message_dict.keys()).index(x))

    def remove_specified_message_id(self, message_id):
        if message_id in self.specified_context_message_list:
            self.specified_context_message_list.remove(message_id)

    def get_messages_length(self):
        """获取 message_dict 的长度"""
        return len(self.message_dict)

    def get_specified_messages_length(self):
        """获取 specified_context_message_list 的长度"""
        return len(self.specified_context_message_list)

    def rename_last_key(self, old_key, new_key):
        """将 message_dict 中的某个键从 old_key 改为 new_key"""
        if old_key not in self.message_dict:
            raise KeyError(f"Old key '{old_key}' not found in message_dict.")

        if new_key in self.message_dict:
            raise KeyError(f"New key '{new_key}' already exists in message_dict.")

        # 获取旧键的值
        value = self.message_dict[old_key]
        # 删除旧键
        del self.message_dict[old_key]
        # 添加新键
        self.message_dict[new_key] = value

        if self.specify_context_message_flag:
            if old_key  in self.specified_context_message_list:
                self.specified_context_message_list.remove(old_key)
                self.specified_context_message_list.append(new_key)



    def pause_and_wait_for_resume(self):
        pass



