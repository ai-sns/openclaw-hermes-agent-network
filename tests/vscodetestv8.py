import requests
import json
import websocket
import time


def raw_websocket_drill():
    cdp_url = "http://localhost:9222"

    # 1. 寻找目标
    try:
        targets = requests.get(f"{cdp_url}/json").json()
    except:
        return

    target_ws = None
    for t in targets:
        if "vscode-webview://" in t.get('url', '') and "index.html" in t.get('url', ''):
            if "service-worker" not in t.get('url', ''):
                target_ws = t.get('webSocketDebuggerUrl')
                break

    if not target_ws:
        print("❌ 未找到目标")
        return

    print(f"🔌 连接外壳: {target_ws}")

    try:
        # suppress_origin=True 绕过 403 错误
        ws = websocket.create_connection(target_ws, suppress_origin=True)

        print("🔨 正在尝试 JS 穿透 (Iframe Piercing)...")

        # 循环尝试，因为 iframe 加载需要时间
        for i in range(10):
            # === 核心 JS 脚本 ===
            # 这段 JS 会在浏览器内部执行：
            # 1. 找到页面里的 iframe (通常 id 是 active-frame)
            # 2. 获取它的 contentDocument (内部文档)
            # 3. 提取 body.innerText
            js_script = """
            (() => {
                // 1. 找 iframe
                const iframe = document.getElementById('active-frame') || document.querySelector('iframe');
                if (!iframe) return { status: 'no_iframe' };

                try {
                    // 2. 尝试进入 iframe 内部
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!doc) return { status: 'cross_origin' }; // 如果被安全策略拦截

                    // 3. 拿数据
                    const text = doc.body.innerText;
                    return { 
                        status: 'success', 
                        text: text,
                        length: text.length
                    };
                } catch (e) {
                    return { status: 'error', msg: e.toString() };
                }
            })()
            """

            payload = {
                "id": i,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_script,
                    "returnByValue": True
                }
            }

            ws.send(json.dumps(payload))
            response = json.loads(ws.recv())

            # 解析结果
            try:
                result = response['result']['result']['value']
                status = result.get('status')

                if status == 'success':
                    content = result.get('text', '')
                    if len(content.strip()) > 0:
                        print("\n" + "=" * 40)
                        print("🏆 穿透成功！内容如下：")
                        print("=" * 40)
                        print(content)
                        print("=" * 40)
                        break
                    else:
                        print(f"   ⏳ [第 {i + 1}次] Iframe 内部是空的，等待渲染...")

                elif status == 'no_iframe':
                    print(f"   ⚠️ [第 {i + 1}次] 还没看到 iframe 标签...")
                elif status == 'cross_origin':
                    print(f"   ❌ [第 {i + 1}次] 跨域拦截！无法直接读取 iframe。")
                    # 如果遇到这个，说明内部 iframe 是独立进程，需要换策略，但先试试
                else:
                    print(f"   ⚠️ 状态: {status}")

            except KeyError:
                pass

            time.sleep(1)

        ws.close()

    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    raw_websocket_drill()
