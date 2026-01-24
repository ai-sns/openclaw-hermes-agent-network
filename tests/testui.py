import sys
from uiautomation import *


# === 核心递归查找函数 ===
# 这种写法最稳健，不依赖库的高级遍历功能，只要能获取 Children 就能跑
def find_specific_text(control, target_keyword, depth):
    # 1. 深度安全锁：防止 Electron 无限层级卡死
    if depth > 15:
        return None

    # 2. 获取子元素
    children = control.GetChildren()

    for child in children:
        # --- 判断逻辑 ---
        # 必须同时满足：是文本控件 + 内容包含关键词
        if child.ControlTypeName == 'TextControl' and target_keyword in child.Name:
            return child  # 找到了！直接返回这个控件对象

        # --- 递归继续找 ---
        result = find_specific_text(child, target_keyword, depth + 1)
        if result:
            return result  # 如果在深层找到了，就一路返回上来

    return None


# === 主程序 ===
def main():
    # 1. 连接 VS Code
    print("正在连接 VS Code...")
    vscode = WindowControl(RegexName='.*Visual Studio Code')

    if not vscode.Exists(3):
        print("❌ 未找到 VS Code 窗口")
        return

    vscode.SetFocus()

    # 2. 定位锚点 "Codex" 面板
    # 这里的 SearchDepth=20 是为了在整个窗口里找到 Codex 区域
    print("正在定位 'Codex' 面板...")
    codex_panel = vscode.DocumentControl(Name="Codex", SearchDepth=20)

    if not codex_panel.Exists(2):
        print("⚠️ 未找到 'Codex' 文档，尝试在侧边栏查找...")
        # 备用方案：如果 Codex 没显示名字，可能是在 Sidebar 下的第一个 Document
        sidebar = vscode.GroupControl(ClassName='Sidebar', SearchDepth=10)
        codex_panel = sidebar.DocumentControl(SearchDepth=5)

    if codex_panel.Exists(1):
        print(f"✅ 锁定搜索区域: {codex_panel.Name}")
        print("正在搜索目标文本...")

        # 3. 开始精准查找
        # 关键词取前几个词即可，防止标点符号不匹配
        target_keyword = "Hey there! Ready when you are"

        target_element = find_specific_text(codex_panel, target_keyword, 0)

        if target_element:
            print("\n" + "=" * 40)
            print("🎯 成功捕获目标！")
            print("=" * 40)
            print(f"完整内容: {target_element.Name}")
            print(f"控件类型: {target_element.ControlTypeName}")
            print(f"坐标范围: {target_element.BoundingRectangle}")
            print("=" * 40)

            # 💡 你可以在这里对 target_element 做操作，比如获取它的全部文本
            # full_text = target_element.Name
        else:
            print(f"❌ 在 'Codex' 面板下未找到包含 '{target_keyword}' 的文本。")
            print("可能原因：")
            print("1. 面板未滚动到该消息（VS Code 懒加载，不可见的一般读不到）。")
            print("2. 文本内容有细微差别（空格或符号）。")

    else:
        print("❌ 无法定位到插件面板区域。")


if __name__ == '__main__':
    main()
