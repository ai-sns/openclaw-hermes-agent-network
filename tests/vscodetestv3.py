from playwright.sync_api import sync_playwright
import time


def get_codex_force():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")

        # 1. 找到主窗口 (通常标题包含 Visual Studio Code)
        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "Visual Studio Code" in page.title():
                    target_page = page
                    break
            if target_page: break

        if not target_page:
            print("❌ 未找到 VS Code 主窗口，请确认 VS Code 已在前台运行")
            return

        print(f"✅ 锁定主窗口: {target_page.title()}")

        # 2. 暴力递归查找所有 Frame
        # VS Code 的插件通常藏在：Page -> Iframe (Webview容器) -> Iframe (Active) -> 实际内容

        found_frame = None

        # 遍历所有 frame
        for frame in target_page.frames:
            # 过滤掉无关的系统 frame
            if "webview" not in frame.url:
                continue

            print(f"🔎 检查 Webview Frame: {frame.url[:40]}...")

            try:
                # 策略：检查 frame 内部是否有特定的 HTML 元素
                # 大多数聊天插件都有输入框 (textarea 或 input)
                # 或者特定的 class，你可以先用 "body" 试试能不能拿到所有文字

                # 获取该 frame 下的所有文本
                text = frame.inner_text("body", timeout=1000)

                if text and len(text) > 0:
                    print(f"   📄 发现文本 (长度{len(text)}): {text[:30].replace(chr(10), ' ')}...")

                    # 在这里修改你的关键词！
                    # 如果你的插件叫 Codex，里面可能包含 "Ask", "Chat", "AI" 等字眼
                    if "Ready" in text or "Codex" in text or "Type" in text:
                        print("   🎯 锁定目标 Frame!")
                        found_frame = frame
                        break
            except Exception as e:
                # 忽略读取超时的 frame
                continue

        if found_frame:
            print("\n" + "=" * 30)
            print("🎉 成功获取数据:")
            # 打印完整的聊天记录
            print(found_frame.inner_text("body"))
            print("=" * 30)
        else:
            print("❌ 遍历结束，仍未找到。可能是关键词不匹配，请查看上面的“发现文本”自行调整关键词。")


if __name__ == "__main__":
    get_codex_force()
