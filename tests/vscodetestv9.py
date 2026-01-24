# "C:\Users\IDD\AppData\Local\Programs\Microsoft VS Code\Code.exe"  --remote-debugging-port=9222 --remote-allow-origins=*
import requests
import json
import websocket
import time


def universal_bot_extractor():
    cdp_url = "http://localhost:9222"

    # 1. 获取所有 CDP 目标
    print(f"🔍 扫描调试端口: {cdp_url}/json")
    try:
        targets = requests.get(f"{cdp_url}/json").json()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 2. 筛选出所有可能的 Webview (不只是 Cline)
    webview_targets = []
    for t in targets:
        url = t.get('url', '')
        # 排除 Service Worker，只留 UI 界面
        if "vscode-webview://" in url and "service-worker" not in url:
            # 排除空的或者背景页，通常 UI 界面包含 index.html
            if "index.html" in url:
                webview_targets.append(t)

    if not webview_targets:
        print("❌ 未找到任何 Webview UI 目标。")
        return

    print(f"📋 找到 {len(webview_targets)} 个潜在插件窗口，开始逐个扫描...")

    # 3. 遍历每一个 Webview (防止你同时开了 Codex 和 Cline，我们都试一遍)
    for t in webview_targets:
        ws_url = t.get('webSocketDebuggerUrl')
        title = t.get('title', 'Unknown')
        print(f"\n🔌 正在连接: {title[:40]}...")

        try:
            ws = websocket.create_connection(ws_url, suppress_origin=True)

            # === 核心：通用 JS 探测脚本 ===
            # 这个脚本非常智能：
            # 1. 先找 iframe (Cline 模式)
            # 2. 如果没 iframe，直接读 Body (Codex 模式)
            # 3. 同时处理了 Shadow DOM 的可能性
            js_script = """
            (() => {
                // 辅助函数：清理文本
                const clean = (text) => text ? text.trim() : '';

                // --- 策略 A: 尝试穿透 Iframe (针对 Cline) ---
                const iframe = document.querySelector('iframe');
                if (iframe) {
                    try {
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        if (doc) {
                            const text = doc.body.innerText;
                            if (clean(text).length > 0) {
                                return { type: 'iframe_mode', text: text };
                            }
                        }
                    } catch(e) { 
                        // 跨域忽略，继续尝试策略 B
                    }
                }

                // --- 策略 B: 直接读取 Body (针对 Codex) ---
                const directText = document.body.innerText;

                // --- 策略 C: 简单的 Shadow DOM 探测 (针对复杂 UI) ---
                // 有些插件把内容藏在 ShadowRoot 里
                // 这里做一个简单的遍历
                let shadowText = '';
                if (clean(directText).length < 50) { // 如果主 Body 没啥内容
                    const allNodes = document.querySelectorAll('*');
                    for (const node of allNodes) {
                        if (node.shadowRoot) {
                            shadowText += node.shadowRoot.textContent + '\\n';
                        }
                    }
                }

                // 决策返回
                if (clean(shadowText).length > clean(directText).length) {
                    return { type: 'shadow_mode', text: shadowText };
                }

                return { type: 'direct_mode', text: directText };
            })()
            """

            # 尝试 3 次，等待加载
            found_content = False
            for i in range(3):
                payload = {
                    "id": i,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_script,
                        "returnByValue": True
                    }
                }
                ws.send(json.dumps(payload))
                res = json.loads(ws.recv())

                try:
                    val = res['result']['result']['value']
                    mode = val.get('type')
                    text = val.get('text', '')

                    if len(text.strip()) > 50:  # 过滤掉只有几个字的空页面
                        print("\n" + "=" * 50)
                        print(f"🏆 抓取成功! (模式: {mode})")
                        print(f"📄 来源: {title}")
                        print("=" * 50)
                        print(text[:2000])  # 打印前2000字，避免刷屏
                        print("=" * 50)
                        found_content = True
                        break
                    else:
                        pass  # 内容太短，可能是加载中或空页面

                except Exception:
                    pass

                time.sleep(0.5)

            if not found_content:
                print("   ⚠️ 此窗口无有效文本内容。")

            ws.close()

        except Exception as e:
            print(f"   ❌ 连接错误: {e}")


if __name__ == "__main__":
    universal_bot_extractor()
