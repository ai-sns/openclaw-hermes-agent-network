import requests
import json
import websocket
import time


class VSCodeController:
    def __init__(self):
        self.ws = None
        self.cdp_url = "http://localhost:9222"

    def connect_target(self):
        """自动寻找并连接 Codex 或 Cline"""
        try:
            targets = requests.get(f"{self.cdp_url}/json").json()
        except:
            print("❌ 无法连接 VS Code 调试端口")
            return False

        # 筛选 Webview
        for t in targets:
            url = t.get('url', '')
            if "vscode-webview://" in url and "index.html" in url and "service-worker" not in url:
                self.ws = websocket.create_connection(t.get('webSocketDebuggerUrl'), suppress_origin=True)
                print(f"✅ 已连接: {t.get('title')}")
                return True
        print("❌ 未找到 Webview 目标")
        return False

    def find_and_click(self, keyword):
        """
        在页面中寻找包含 keyword 的元素，获取坐标并点击
        """
        if not self.ws: return

        print(f"🔍 正在寻找按钮: '{keyword}' ...")

        # === 核心 JS：智能定位 + 坐标计算 + 点击 ===
        # 这段 JS 会自动计算 iframe 的偏移量，返回绝对坐标
        js_script = f"""
        (() => {{
            const targetText = "{keyword}".toLowerCase();

            // 辅助：检查元素文本
            function matches(el) {{
                return (el.innerText || el.textContent || '').toLowerCase().includes(targetText) ||
                       (el.getAttribute('aria-label') || '').toLowerCase().includes(targetText) ||
                       (el.getAttribute('title') || '').toLowerCase().includes(targetText);
            }}

            // 1. 递归搜索所有可能的文档 (Main, Iframe, ShadowDOM)
            function searchInRoot(root, offset = {{x:0, y:0}}) {{
                // 尝试找 button, a, 或者 role=button 的 div
                const candidates = root.querySelectorAll('button, a, [role="button"], div[class*="button"]');

                for (let el of candidates) {{
                    if (matches(el)) {{
                        const rect = el.getBoundingClientRect();
                        return {{
                            found: true,
                            x: rect.x + offset.x + rect.width / 2, // 中心点 X
                            y: rect.y + offset.y + rect.height / 2, // 中心点 Y
                            width: rect.width,
                            height: rect.height,
                            text: el.innerText.substring(0, 20)
                        }};
                    }}
                }}
                return null;
            }}

            // --- A. 检查主文档 ---
            let result = searchInRoot(document);
            if (result) {{
                // 执行 JS 点击 (最稳)
                // document.elementFromPoint(result.x, result.y).click(); 
                // 或者直接再次查询点击，这里为了演示坐标，我们返回坐标让 Python 决定
            }}

            // --- B. 检查 Iframe (针对 Cline) ---
            if (!result) {{
                const iframe = document.querySelector('iframe');
                if (iframe) {{
                    try {{
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const rect = iframe.getBoundingClientRect();
                        // 递归搜 iframe，并加上 iframe 本身的偏移量
                        result = searchInRoot(doc, {{x: rect.x, y: rect.y}});
                    }} catch(e) {{}}
                }}
            }}

            // --- C. 执行点击 ---
            // 为了保证成功率，我们直接在 JS 里触发一次 .click()
            // 同时把坐标传回给 Python，如果你想用模拟鼠标的话
            if (result) {{
                // 重新定位元素进行点击 (简化逻辑，实际场景可以直接缓存引用)
                // 这里我们返回坐标，证明找到了
                return result;
            }}

            return {{ found: false }};
        }})()
        """

        # 发送指令
        payload = {
            "id": int(time.time()),
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_script,
                "returnByValue": True
            }
        }

        self.ws.send(json.dumps(payload))
        res = json.loads(self.ws.recv())

        try:
            data = res['result']['result']['value']

            if data.get('found'):
                x = data['x']
                y = data['y']
                print(f"🎉 找到目标: [{data['text']}...]")
                print(f"📍 页面坐标: X={x}, Y={y} (尺寸: {data['width']}x{data['height']})")

                # === 动作 A: 通过 CDP 模拟物理点击 (Input Domain) ===
                # 这比 JS click 更像真实用户，能触发 :hover 等效果
                self._cdp_mouse_click(x, y)
                print("🖱️ 已发送物理点击指令")

                return True
            else:
                print("⚠️ 未找到包含该文字的按钮")
                return False

        except Exception as e:
            print(f"❌ 解析错误: {e}")
            return False

    def _cdp_mouse_click(self, x, y):
        """发送 CDP 鼠标事件"""
        # 1. 鼠标按下
        self.ws.send(json.dumps({
            "id": int(time.time()),
            "method": "Input.dispatchMouseEvent",
            "params": {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }
        }))

        # 2. 鼠标松开
        self.ws.send(json.dumps({
            "id": int(time.time()) + 1,
            "method": "Input.dispatchMouseEvent",
            "params": {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }
        }))

    def close(self):
        if self.ws: self.ws.close()


if __name__ == "__main__":
    bot = VSCodeController()
    if bot.connect_target():
        # === 测试 1: 点击 "Copy" 按钮 ===
        # 请根据你界面上实际存在的按钮文字修改
        bot.find_and_click("自动提供背景信息")

        # === 测试 2: 点击输入框 (模拟聚焦) ===
        bot.find_and_click("向 Codex 下达任意指令")

        # bot.find_and_click("Plan")
        #
        # # === 测试 2: 点击输入框 (模拟聚焦) ===
        # bot.find_and_click("Act")

        bot.close()
