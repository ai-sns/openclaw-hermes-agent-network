from playwright.sync_api import sync_playwright


def inventory_check():
    # 你的目标 ID
    target_id = "2f171150-4bec-4222-ba0e-f29536ae8f19"

    with sync_playwright() as p:
        print("🔗 连接 VS Code (9222)...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")

        print(f"\n📋 开始资产盘点 (寻找目标: {target_id})")
        print("=" * 60)

        found = False
        frame_count = 0

        # 遍历所有 Context
        for i, ctx in enumerate(browser.contexts):
            # 遍历所有 Page
            for j, page in enumerate(ctx.pages):
                print(f"\n📄 [Context {i} | Page {j}] 标题: {page.title()}")

                # 遍历所有 Frame
                for frame in page.frames:
                    frame_count += 1
                    # 获取 frame 的 name 属性（这是 Playwright 认为的名字）
                    p_name = frame.name

                    # 尝试获取 HTML 标签上的 name 属性 (这是 Inspector 看到的名字)
                    # 有时候 frame.name 是空的，但 HTML 标签里有 name
                    try:
                        html_name = frame.evaluate("window.name")
                    except:
                        html_name = "无法读取"

                    url_preview = frame.url[-40:] if len(frame.url) > 40 else frame.url

                    # 打印匹配情况
                    is_match = (target_id == p_name) or (target_id == html_name)
                    marker = "✅✅✅ 找到了！！！" if is_match else ""

                    if is_match: found = True

                    print(f"   Frame: Name='{p_name}' | HTML_Name='{html_name}' | URL=...{url_preview} {marker}")

        print("=" * 60)
        print(f"统计: 共扫描了 {frame_count} 个 Frame。")

        if found:
            print("结论: Playwright 能看到它！之前的脚本逻辑有问题。")
        else:
            print("结论: Playwright 根本看不到这个 Frame。")
            print("可能原因：")
            print("1. 它是 Webview 进程，需要独立连接（见下一步）。")
            print("2. ID 真的变了（Inspector 里的信息可能是旧的缓存）。")


if __name__ == "__main__":
    inventory_check()
