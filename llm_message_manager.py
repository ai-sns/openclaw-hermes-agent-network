class LLMMessageManager:
    def __init__(self):
        # 初始化一个字典和几个列表
        self.message_dict = {}
        self.specified_context_message_list = []
        self.specify_context_message_flag = False

    def re_init(self):
        # 清空字典和列表，重置标志
        self.message_dict.clear()
        self.specified_context_message_list.clear()
        self.specify_context_message_flag = False

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







