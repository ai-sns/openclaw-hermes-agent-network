import sys
import time
import uiautomation as auto

# 设置超时
auto.SetGlobalSearchTimeout(3)


class ClineScraper:
    def __init__(self):
        self.vscode = None
        self.cline_doc = None  # Cline 的主文档区域
        self.captured_texts = []
        self.seen_hashes = set()

    def connect_vscode(self):
        print("🔗 正在连接 VS Code...")
        self.vscode = auto.WindowControl(RegexName='.*Visual Studio Code')
        if not self.vscode.Exists(3):
            print("❌ 未找到 VS Code 窗口")
            return False
        self.vscode.SetFocus()
        return True

    def find_cline_area(self):
        print("🔍 正在定位 Cline 面板...")

        # 1. 第一步：根据 Ancestors 信息，先找到 Name="Cline" 的 Document
        # Depth 设大一点，防止嵌套过深
        self.cline_doc = self.vscode.DocumentControl(Name="Cline", SearchDepth=20)

        if not self.cline_doc.Exists(1):
            # 备用：尝试模糊查找
            self.cline_doc = self.vscode.DocumentControl(
                searchDepth=20,
                compare=lambda c, d: "Cline" in c.Name if c.Name else False
            )

        if self.cline_doc.Exists(1):
            print(f"✅ 找到 Cline 文档区域: {self.cline_doc.Name}")

            # 2. 唤醒 UI 树 (点击中心)
            # Inspect 显示这通常是一个可滚动的区域
            print("👆 激活区域...")
            try:
                self.cline_doc.Click(simulateMove=True)
            except:
                rect = self.cline_doc.BoundingRectangle
                cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
                auto.Click(cx, cy)

            return True
        else:
            print("❌ 未找到 Cline 文档。请确认侧边栏已打开 Cline。")
            return False

    def _extract_content(self):
        """
        根据 inspect.exe 发现的规律：
        目标内容的 ControlType 是 Group (组)
        ClassName 是 "scrollable grow overflow-y-scroll" (或者包含它)
        Name 属性直接包含了所有文本
        """
        found_count = 0

        # 遍历 Cline 文档下的所有控件
        # 我们寻找符合 inspect 特征的 GroupControl
        for ctrl, depth in auto.WalkControl(self.cline_doc, includeTop=False, maxDepth=15):
            # 过滤 1: 必须是 GroupControl (组)
            if ctrl.ControlTypeName != 'GroupControl':
                continue

            # 过滤 2: 只要 Name 有内容
            raw_text = ctrl.Name
            if not raw_text or len(raw_text.strip()) < 2:
                continue

            # 过滤 3 (可选): 根据 ClassName 精确匹配
            # 你的 inspect 显示 ClassName 是 "scrollable grow overflow-y-scroll"
            # 我们只要匹配 "scrollable" 或 "overflow" 即可
            # 注意：某些子气泡可能没有这个 class，所以这个条件可以视情况注释掉
            # if "scrollable" not in ctrl.ClassName and "overflow" not in ctrl.ClassName:
            #    continue

            # 去重处理
            text_hash = hash(raw_text)
            if text_hash not in self.seen_hashes:
                self.seen_hashes.add(text_hash)

                # 简单清洗：inspect 显示名字里包含一些 Unicode 图标 (如 )，可以不用管，或者替换掉
                clean_text = raw_text.strip()
                self.captured_texts.append(clean_text)
                found_count += 1

                print(f"   [抓取] {clean_text[:60].replace(chr(10), ' ')}...")

        return found_count

    def run(self):
        if not self.connect_vscode(): return
        if not self.find_cline_area(): return

        print("\n⬆️ 预滚动 (加载历史)...")
        # 对着 Cline 文档区域滚动
        # 注意：如果 document 不响应滚动，可能需要找到那个特定的 class="scrollable..." 的控件来滚动
        # 这里先尝试对着 Document 滚
        for _ in range(3):
            auto.WheelUp(wheelTimes=3)
            time.sleep(0.5)

        print("\n⬇️ 开始抓取...")
        no_new_data = 0

        while True:
            count = self._extract_content()

            if count == 0:
                no_new_data += 1
            else:
                no_new_data = 0

            # 连续 8 次没新内容才停止
            if no_new_data >= 8:
                print("🏁 抓取结束。")
                break

            # 向下滚动
            auto.WheelDown(wheelTimes=3)
            time.sleep(1.0)  # 等待 Electron 渲染

    def save(self):
        print(f"\n📊 共抓取 {len(self.captured_texts)} 条记录。")
        if not self.captured_texts:
            return

        with open("cline_chat_history.txt", "w", encoding="utf-8") as f:
            for t in self.captured_texts:
                f.write(t + "\n" + "=" * 50 + "\n")
        print("📁 保存至 cline_chat_history.txt")


if __name__ == '__main__':
    s = ClineScraper()
    s.run()
    s.save()
