import time
from playwright.sync_api import sync_playwright


def get_codex_content_v8():
    target_id = "2f171150-4bec-4222-ba0e-f29536ae8f19"

    with sync_playwright() as p:
        print("🔗 连接 VS Code...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]

        # === 1. 定位外壳 (Shell) ===
        print(f"🎯 正在定位外壳 (ID: {target_id})...")
        shell_frame = None

        for attempt in range(5):
            for frame in page.frames:
                try:
                    if frame.evaluate("window.name") == target_id:
                        shell_frame = frame
                        break
                except: continue
            if shell_frame: break
            time.sleep(1)

        if not shell_frame:
            print("❌ 找不到外壳，ID可能变了。")
            return

        print("✅ 找到外壳 Frame。")

        # === 2. 核心修复：通过 ElementHandle 获取真正的 Frame 对象 ===
        print("⚡ 正在把 iframe 标签转换为 Frame 对象...")

        inner_frame = None

        # 轮询
        for i in range(10):
            try:
                # [关键步骤 A] 获取 iframe 的元素句柄 (ElementHandle)，而不是 Locator
                # wait_for_selector 返回的是 ElementHandle
                iframe_handle = shell_frame.wait_for_selector("iframe", timeout=1000)

                if iframe_handle:
                    # [关键步骤 B] 从句柄获取 Frame 对象
                    # 这才是真正的 Frame，拥有 .url 和 .inner_text 方法
                    inner_frame = iframe_handle.content_frame()

                    if inner_frame:
                        print(f"🎉 成功锁定! URL: {inner_frame.url[:50]}...")
                        break
            except Exception as e:
                pass  # 忽略超时

            time.sleep(1)
            print(f"   ⏳ 等待加载... ({i + 1}/10)")

        if not inner_frame:
            print("❌ 无法获取内部 Frame 对象。")
            return

        # === 3. 提取内容 ===
        print("\n📖 正在读取内容...")
        try:
            # 现在 inner_frame 是真正的 Frame 对象了，可以使用 wait_for_selector
            inner_frame.wait_for_selector("body", timeout=5000)

            # 获取文本
            text = inner_frame.inner_text("body")

            print("\n" + "=" * 40)
            print("🏆 抓取成功 🏆")
            print("=" * 40)
            print(text)
            print("=" * 40)

        except Exception as e:
            print(f"❌ 读取内容失败: {e}")


if __name__ == "__main__":
    get_codex_content_v8()
