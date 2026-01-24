import time
import json
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Frame, Locator


class VSCodeCodexScraper:
    def __init__(self, port: int = 9222):
        self.port = port
        self.browser = None
        self.playwright = None
        self.target_frame: Optional[Frame] = None

    def connect(self):
        """连接到 VS Code 实例"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{self.port}")
            print(f"✅ 成功连接到 VS Code (Port {self.port})")
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("请确保 VS Code 已通过命令行启动: --remote-debugging-port=9222")
            raise e

    def find_codex_webview(self, keyword="Codex") -> bool:
        """
        在所有上下文中寻找包含特定关键词的 Webview (iframe)。
        VS Code 的插件通常运行在 iframe 中。
        """
        # 遍历所有上下文（Context）和页面（Page）
        for context in self.browser.contexts:
            for page in context.pages:
                # 遍历页面内的所有 iframe
                for frame in page.frames:
                    try:
                        # 策略：检测 frame 内部是否包含 Codex 相关的特定元素或文本
                        # 这里我们用一种通用的方式：检查 frame 标题或内部文本
                        # 注意：Codex 插件的具体特征可能需要根据实际 DOM 微调

                        # 1. 尝试通过 URL 或 Name 过滤 (VS Code webview url 通常很长)
                        if "webview" not in frame.url:
                            continue

                        # 2. 尝试获取内容判断
                        # 假设 Codex 界面里一定有某些特征词，比如 "Codex" 或者输入框
                        # 你可以根据实际情况修改这个选择器，比如 '.chat-input'
                        content = frame.content()
                        if keyword in content or "chat" in content.lower():
                            self.target_frame = frame
                            print(f"✅ 锁定目标 Webview: {frame.url[:50]}...")
                            return True
                    except Exception as e:
                        continue

        print("❌ 未找到目标 Codex 面板，请确认面板已在 VS Code 中打开。")
        return False

    def scroll_to_load_history(self, max_scrolls=10):
        """
        模拟滚动以触发懒加载 (Lazy Loading)。
        通常聊天记录需要向上滚动才能加载更多。
        """
        if not self.target_frame:
            raise Exception("未选定目标 Frame")

        print("🔄 开始滚动加载历史记录...")

        # 定位滚动容器。
        # 注意：不同的插件 HTML 结构不同。
        # 大多数 VS Code 聊天插件的主容器是 body 或某个 class 为 scrollable 的 div
        # 这里我们尝试直接滚动 body
        scroll_selector = "body"

        previous_height = 0

        for i in range(max_scrolls):
            # 获取当前高度
            current_height = self.target_frame.evaluate("document.body.scrollHeight")

            # 策略：先滚到顶部触发加载，再滚到底部
            # 1. 滚到顶部 (加载旧消息)
            self.target_frame.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)  # 等待 DOM 渲染

            # 2. 滚到底部 (为了截图或保持视觉一致，可选)
            # self.target_frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            new_height = self.target_frame.evaluate("document.body.scrollHeight")

            if new_height == previous_height:
                # 高度不再变化，说明可能加载完了
                print(f"🛑 滚动停止，高度未变化 (迭代: {i})")
                break

            previous_height = new_height
            print(f"📜 第 {i + 1} 次滚动加载完成...")

    def extract_messages(self) -> List[Dict]:
        """
        提取对话内容。
        需要根据 Codex 具体的 HTML 结构调整 CSS 选择器。
        """
        if not self.target_frame:
            raise Exception("未选定目标 Frame")

        messages = []

        # === 核心选择器配置 (需要根据 Inspect 结果微调) ===
        # 假设：聊天气泡通常是 div，可能包含 class 'message', 'chat-item' 等
        # 如果你不知道具体 class，可以提取所有文本段落

        # 方案 A: 通用抓取 (抓取所有非空文本块)
        # elements = self.target_frame.locator("div, p, span").all()

        # 方案 B: 针对性抓取 (假设结构如下，需要你用 Developer Tools 确认一下)
        # 这里的 selector 是基于常见的 Chat UI 猜测的
        message_elements = self.target_frame.locator(".conversation-message, .chat-message, .message-content, [role='listitem']").all()

        if not message_elements:
            print("⚠️ 未通过特定选择器找到消息，尝试提取全部可见文本...")
            full_text = self.target_frame.locator("body").inner_text()
            return [{"type": "raw", "content": full_text}]

        print(f"🔍 找到 {len(message_elements)} 条消息元素，正在解析...")

        for idx, el in enumerate(message_elements):
            try:
                text = el.inner_text()
                if not text.strip():
                    continue

                # 尝试判断是谁发的 (通过 class 或位置)
                # 比如 class 包含 'user' 或 'me'
                class_attr = el.get_attribute("class") or ""
                sender = "User" if "user" in class_attr.lower() or "right" in class_attr.lower() else "AI"

                messages.append({
                    "id": idx,
                    "sender": sender,
                    "content": text,
                    "raw_class": class_attr
                })
            except:
                continue

        return messages

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


# === 使用示例 ===
def main():
    scraper = VSCodeCodexScraper()

    try:
        # 1. 连接
        scraper.connect()

        # 2. 定位 (确保你在 VS Code 已经打开了 Codex 面板)
        # 你可以传入你在面板上看到的独特关键词，比如 "Ask Codex" 或 "Type here"
        if scraper.find_codex_webview(keyword="Ready when you are"):
            # 3. 滚动加载 (可选)
            scraper.scroll_to_load_history(max_scrolls=3)

            # 4. 导出
            data = scraper.extract_messages()

            # 5. 保存或打印
            print("\n" + "=" * 40)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("=" * 40)

            # 保存到文件
            with open("codex_chat_history.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"📁 已保存 {len(data)} 条消息到 codex_chat_history.json")

    except Exception as e:
        print(f"程序执行出错: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
