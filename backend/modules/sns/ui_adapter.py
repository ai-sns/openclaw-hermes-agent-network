class UIAdapter:
    def __init__(self,parent):
        self.parent = parent

    def get_ai_model_display_name(self):
        """
        获取AI模型显示名称，格式为"🧠 {provider} {model_name}"
        """
        try:
            from db.DBFactory import query_AgentCfg

            # 获取账户信息
            snsaccount = self.parent.aichatcfg_record.account
            agent_cfg = query_AgentCfg(snsaccount=snsaccount)

            # 获取默认模型
            if agent_cfg and agent_cfg.defaultmodel:
                defaultmodel = agent_cfg.defaultmodel
                return f"🧠 {defaultmodel}"
            else:
                return "🧠 OpenAI gpt-4o-mini"  # 默认值
        except Exception as e:
            print(f"获取AI模型名称时出错: {e}")
            return "🧠 OpenAI gpt-4o-mini"  # 出错时的默认值

    def update_resource_display(self):
        """
        更新资源显示内容，包括工具列表、人员名单和地址列表
        """
        # 获取各类资源数据
        tool_list = self.parent.get_tool_list()
        people_list = self.parent.get_people_list()
        place_list = self.parent.get_place_list()

        # 格式化内容
        formatted_content = self._format_resource_content(tool_list, people_list, place_list)+"\n"

        # 发送到前端 Resource 页签
        import asyncio
        asyncio.create_task(self.parent._send_to_frontend('resource', formatted_content))

    def _format_resource_content(self, tool_list, people_list, place_list):
        """
        格式化资源内容显示
        """
        content = ""

        # 格式化工具列表
        if tool_list:
            content += f"🌐 服务列表（共 {len(tool_list)} 项）\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            for i, tool in enumerate(tool_list):
                # 工具ID和名称
                content += f"#{tool.get('id', '')} {tool.get('name', '')}\n"


                # 地理坐标信息（如果lng,lat有值且不为0）
                lng = tool.get('lng', 0)
                lat = tool.get('lat', 0)
                if lng and lat and lng != 0 and lat != 0:
                    # 格式化坐标，最多8位小数，去除尾随零
                    formatted_lng = f"{lng:.8g}"
                    formatted_lat = f"{lat:.8g}"
                    content += f"📍 坐标：{formatted_lng}, {formatted_lat}\n"
                elif 'place' in tool and tool['place']:
                    content += f"🌍 位置：{tool['place']}\n"

                # 描述信息
                if 'description' in tool and tool['description']:
                    content += f"💬 描述：{tool['description']}\n"

                # 地址信息
                if 'address' in tool and tool['address'] and tool['address'] != "Not needed":
                    content += f"🔗 地址：{tool['address']}\n"

                # 类型和方法信息
                type_info = tool.get('type', '')
                method_info = tool.get('method', '')

                # 参数信息
                param_info = ""
                if 'parameter' in tool and tool['parameter']:
                    if isinstance(tool['parameter'], dict):
                        param_strs = [f"{k}={v}" for k, v in tool['parameter'].items()]
                        param_info = f"({', '.join(param_strs)})" if param_strs else ""
                    else:
                        param_info = f"({tool['parameter']})" if tool['parameter'] != "None" else ""

                content += f"⚙️ 类型：{type_info} ｜ 方法：{method_info}{param_info}\n"

                # 分隔线（除了最后一个工具）
                if i < len(tool_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n\n"

        # 格式化人员名单
        if people_list:
            content += f"🧑‍🤝‍🧑 人员名单（共 {len(people_list)} 位）\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            for i, person in enumerate(people_list):
                # 姓名和职业
                nick_name = person.get('nick_name', '')
                profession = person.get('profession', '')
                content += f"🧑‍ {nick_name} ｜ 👩‍💻 {profession}\n"

                # 位置信息
                location = person.get('location', [])
                if location and len(location) >= 2:
                    lng, lat = location[0], location[1]
                    # 简化城市信息

                    # 格式化经纬度，最多显示8位小数，不补零
                    formatted_lng = f"{lng:.8f}".rstrip('0').rstrip('.')
                    formatted_lat = f"{lat:.8f}".rstrip('0').rstrip('.')
                    content += f"📍 位置：{formatted_lng}, {formatted_lat}\n"

                # 账户信息
                account = person.get('account', '')
                if account:
                    content += f"💬 account: {account}\n"

                # SNS信息
                sns_url = person.get('sns_url', '')
                if sns_url:
                    content += f"🔗 sns: {sns_url}\n"

                # ID信息
                nation_id = person.get('nation_id', '')
                if nation_id:
                    content += f"🆔 nation_id: {nation_id}\n"

                # 简介信息
                profile = person.get('profile', '')
                if profile:
                    content += f"📝 profile: {profile}\n"

                # 分隔线（除了最后一个人）
                if i < len(people_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n\n"

        # 格式化地址列表
        if place_list:
            content += f"🗺️ 地址列表（共 {len(place_list)} 处）\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            for i, place in enumerate(place_list):
                # 地点名称
                place_name = place.get('place_name', '')
                content += f"🏞️ {place_name}\n"

                # 位置坐标
                position = place.get('place_position', [])
                if position and len(position) >= 2:
                    lng, lat = position[0], position[1]
                    # 格式化经纬度，最多显示8位小数，不补零
                    formatted_lng = f"{lng:.8f}".rstrip('0').rstrip('.')
                    formatted_lat = f"{lat:.8f}".rstrip('0').rstrip('.')
                    content += f"📍 {formatted_lng}, {formatted_lat}\n"

                # 描述信息
                description = place.get('description', '')
                if description:
                    content += f"📖 {description}\n"

                # 分隔线（除了最后一个地点）
                if i < len(place_list) - 1:
                    content += "\n──────────────────────────\n\n"

            content += "\n"

        return content.strip()

    def send_command_to_map(self, command, param_1, param_2):
        """
        发送命令到地图系统

        Args:
            command: 命令类型
            param_1: 参数1
            param_2: 参数2
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # 构建消息
        message = {
            "type": "command",
            "command": command,
            "param_1": param_1,
            "param_2": param_2
        }

        # 异步发送到前端
        async def send_message():
            try:
                await websocket_manager.broadcast(message)
                logger.info(f"Command sent to map: {command}, param_1={param_1}, param_2={param_2}")
            except Exception as e:
                logger.error(f"Failed to send command to map: {e}")

        asyncio.create_task(send_message())

    def send_talk_message(self, fromuser, touser, message):
        """
        发送聊天消息到前端地图

        Args:
            fromuser: 发送者账户
            touser: 接收者账户
            message: 消息内容
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)

        # 构建chatWindow消息（原有格式）
        chat_msg = {
            "type": "chat_message",
            "from": fromuser,
            "to": touser,
            "content": message
        }

        # 构建地图消息（新格式）
        map_msg = {
            "type": "map_chat_message",
            "from_user": fromuser,
            "to_user": touser,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }

        # 异步发送两种格式到前端
        async def send_messages():
            try:
                # 发送到 chatWindow
                await websocket_manager.broadcast(chat_msg)
                # 发送到地图
                await websocket_manager.broadcast(map_msg)
                logger.info(f"Chat messages sent from {fromuser} to {touser}: {message}")
            except Exception as e:
                logger.error(f"Failed to send chat messages: {e}")

        asyncio.create_task(send_messages())

    def show_status_on_map(self, status):
        """
        在地图上显示状态信息

        Args:
            status: 状态信息字符串
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # 构建消息
        msg = {
            "type": "status_update",
            "status": status
        }

        # 异步发送到前端
        async def send_message():
            try:
                await websocket_manager.broadcast(msg)
                logger.info(f"Status update sent: {status}")
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")

        asyncio.create_task(send_message())

    def show_alert_on_map(self, message, is_error=False):
        """
        在地图上显示警告/提示信息

        Args:
            message: 警告/提示信息
            is_error: 是否为错误信息，默认False
        """
        import asyncio
        from backend.shared.websocket_manager import manager as websocket_manager
        import logging

        logger = logging.getLogger(__name__)

        # 构建消息
        msg = {
            "type": "alert",
            "message": message,
            "is_error": is_error
        }

        # 异步发送到前端
        async def send_message():
            try:
                await websocket_manager.broadcast(msg)
                logger.info(f"Alert sent: {message} (is_error={is_error})")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

        asyncio.create_task(send_message())
