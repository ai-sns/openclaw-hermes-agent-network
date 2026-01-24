from util import generate_random_id
from db.DBFactory import add_map_activity,query_map_activity_previous,query_AiChatCfg_map_setting,query_AIChatMessages_All_previous
import json

class JsTaskManager:
    def __init__(self,parent):
        # 初始化一个字典和几个列表
        self.parent = parent
        self.message_dict = {}
        self.specified_context_message_list = []
        self.specify_context_message_flag = False
        self.last_record_id = None
        self.last_friend_account = None
        self.last_record_id_chat = None

    def re_init(self):
        # 清空字典和列表，重置标志
        self.message_dict.clear()
        self.specified_context_message_list.clear()
        self.specify_context_message_flag = False
        self.last_record_id = None
        self.last_friend_account = None
        self.last_record_id_chat = None

    def show_information(self,info,type_str="1"):
        command = ("show_information", info, "")
        self.parent.send_msg_to_map(command)
        activity_id = generate_random_id()
        content = info
        add_map_activity(activity_id, content, type_str)

    def show_information_chat_list(self,info,type_str="1"):
        command = ("show_information_chat", info, "")
        self.parent.send_msg_to_map(command)


    def load_information(self,last_record_id=None,count = 20,type_str=None):
        if not last_record_id:
            last_record_id = self.last_record_id
        records = query_map_activity_previous(last_record_id,count,type_str)
        if records:
            for record in records:
                info = record.content
                command = ("load_information", info, "")
                self.parent.send_msg_to_map(command)
                self.last_record_id = record.id


    def load_information_chat(self,count = 20):

        last_friend_account = self.last_friend_account
        last_record_id_chat = self.last_record_id_chat
        owner_account =self.parent.ai_chat_cfg.account

        records = query_AIChatMessages_All_previous(last_record_id_chat,count,owner_account=owner_account, friend_account=last_friend_account)
        if records:
            for record in records:
                content = record.content
                friend_name = record.friend_name
                if record.flag == 0:
                    content = f"[MyAi]:{content}<br><br>{record.create_time.strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    content = f"[{friend_name}]:{content}<br><br>{record.create_time.strftime('%Y-%m-%d %H:%M:%S')}"


                command = ("load_information_chat", content, "")
                self.parent.send_msg_to_map(command)
                self.last_record_id_chat = record.id
                self.last_friend_account = record.friend_account

    def load_map_setting(self):
        record_dict = query_AiChatCfg_map_setting()
        coord_str = record_dict["current_position"]

        # 检查坐标字符串是数组格式还是对象格式
        if coord_str.startswith('[') and coord_str.endswith(']'):
            # 数组格式: [116.31633245364759,39.83663838626669]
            coords = coord_str.strip('[]').split(',')
            lng = float(coords[0].strip())
            lat = float(coords[1].strip())
            coord_dict = {
                "lng": lng,
                "lat": lat
            }
        elif coord_str.startswith('{') and coord_str.endswith('}'):
            # 对象格式: {"lat":39.642516431681564,"lng":-75.89816784164529}
            coord_dict = json.loads(coord_str)
        else:
            # 默认处理方式（假定是数组格式）
            coords = coord_str.strip('[]').split(',')
            lng = float(coords[0].strip())
            lat = float(coords[1].strip())
            coord_dict = {
                "lng": lng,
                "lat": lat
            }

        current_position_str = json.dumps(coord_dict)
        record_dict["current_position"] = current_position_str

        # 确保route_status字段存在且有默认值
        if "route_status" not in record_dict or not record_dict["route_status"]:
            record_dict["route_status"] = "stopped"

        json_string = json.dumps(record_dict, ensure_ascii=False, indent=4)
        info = json_string
        command = ("load_map_setting", info, "")
        self.parent.send_msg_to_map(command)

    def clear_chat_history(self):
        command = ("clear_chat_history", "", "")
        self.parent.send_msg_to_map(command)

    def clear_chat_list(self):
        command = ("clear_chat_list", "", "")
        self.parent.send_msg_to_map(command)


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







