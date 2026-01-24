import sys
import time
import uiautomation as auto

# 设置全局超时
auto.SetGlobalSearchTimeout(2)


class CodexScraper:
    def __init__(self):
        self.vscode = None
        self.codex_panel = None
        self.captured_messages = []
        self.seen_hashes = set()

    def connect_vscode(self):
        print("🔗 正在连接 VS Code...")
        self.vscode = auto.WindowControl(RegexName='.*Visual Studio Code')

        if not self.vscode.Exists(3):
            print("❌ 未找到 VS Code 窗口！")
            return False

        self.vscode.SetFocus()
        return True

    def find_codex_panel(self):
        print("🔍 正在定位 Codex 面板...")
        # 1. 尝试找 Document
        panel = self.vscode.DocumentControl(Name="Codex", SearchDepth=15)

        # 2. 如果找不到，尝试找包含 Codex 字样的任意控件
        if not panel.Exists(1):
            panel = self.vscode.Control(
                searchDepth=15,
                compare=lambda c, d: "Codex" in c.Name if c.Name else False
            )

        if panel.Exists(1):
            print(f"✅ 找到面板: {panel.Name}")
            self.codex_panel = panel
            return True
        else:
            print("❌ 未找到 Codex 面板。请确保插件已打开。")
            return False

    def _extract_visible_text(self):
        """提取当前视野内的所有文本控件"""
        count = 0

        # === 核心修复 ===
        # 使用 auto.WalkControl 替代不存在的 FindAll
        # includeTop=False: 不包含面板自身
        # maxDepth=12: 搜索深度，VS Code 层级很深，建议设为 10-15
        for ctrl, depth in auto.WalkControl(self.codex_panel, includeTop=False, maxDepth=12):
            # 过滤出 TextControl
            if ctrl.ControlTypeName == 'TextControl':
                text = ctrl.Name

                # 过滤空文本
                if not text or text.strip() == "":
                    continue

                # 哈希去重
                msg_hash = hash(text)
                if msg_hash not in self.seen_hashes:
                    self.seen_hashes.add(msg_hash)
                    self.captured_messages.append(text)
                    count += 1
                    # 打印预览 (去除换行符以便显示)
                    print(f"   [抓取] {text[:50].replace(chr(10), ' ')}...")

        return count

    def scrape_all_content(self):
        if not self.codex_panel:
            return

        # 1. 鼠标移动到面板中心，确保滚动事件生效
        rect = self.codex_panel.BoundingRectangle
        center_x = (rect.left + rect.right) // 2
        center_y = (rect.top + rect.bottom) // 2
        auto.SetCursorPos(center_x, center_y)

        print("\n⬆️ 正在向上滚动以加载历史记录...")

        # 这里的 wheelTimes 是滚动的“量”，负数向下，正数向上（取决于库版本，有些库 wheelTimes 只能是正数然后配合 WheelUp）
        # uiautomation 的 WheelUp 只需要次数
        for i in range(10):
            auto.WheelUp(wheelTimes=3)
            time.sleep(0.5)

        print("\n⬇️ 开始向下滚动并抓取内容...")

        no_new_content_count = 0

        while True:
            # 抓取当前屏幕内容
            new_items = self._extract_visible_text()

            if new_items == 0:
                no_new_content_count += 1
            else:
                no_new_content_count = 0

            # 如果连续 5 次滚动都没抓到新东西，说明到底了
            if no_new_content_count >= 5:
                print("🏁 似乎已到达底部或没有新内容。")
                break

            # 向下滚动
            auto.WheelDown(wheelTimes=3)
            time.sleep(0.8)  # 等待 UI 刷新

    def export(self):
        print("\n" + "=" * 40)
        print(f"📊 抓取完成！共 {len(self.captured_messages)} 条文本片段。")
        print("=" * 40)

        with open("codex_full_export.txt", "w", encoding="utf-8") as f:
            for msg in self.captured_messages:
                f.write(msg + "\n" + "-" * 20 + "\n")

        print("📁 内容已保存至 codex_full_export.txt")


def main():
    scraper = CodexScraper()
    if scraper.connect_vscode():
        if scraper.find_codex_panel():
            scraper.scrape_all_content()
            scraper.export()


if __name__ == '__main__':
    main()
