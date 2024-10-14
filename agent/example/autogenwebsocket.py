from datetime import datetime
from tempfile import TemporaryDirectory

from websockets.sync.client import connect  as ws_connect

import autogen
from autogen.io.websockets import IOWebsockets



def on_connect(iostream: IOWebsockets) -> None:
    print(f" - on_connect(): Connected to client using IOWebsockets {iostream}", flush=True)

    print(" - on_connect(): Receiving message from client.", flush=True)

    config_list_claude = [
        {
            # Choose your model name.
            "model": "gpt-3.5-turbo",
            # You need to provide your API key here.
            "api_key": "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",
            # "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "stream": True,
        }
    ]

    # 1. Receive Initial Message
    initial_msg = iostream.input()

    # 2. Instantiate ConversableAgent
    agent = autogen.ConversableAgent(
        name="chatbot",
        system_message="Complete a task given to you and reply TERMINATE when the task is done. If asked about the weather, use tool 'weather_forecast(city)' to get the weather forecast for a city.",
        llm_config={
            "config_list": config_list_claude,
            "stream": True,
        },
    )

    # 3. Define UserProxyAgent
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        system_message="A proxy for the user.",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
    )

    # 4. Define Agent-specific Functions
    def weather_forecast(city: str) -> str:
        return f"The weather forecast for {city} at {datetime.now()} is sunny."

    autogen.register_function(
        weather_forecast, caller=agent, executor=user_proxy, description="Weather forecast for a city"
    )

    # 5. Initiate conversation
    print(
        f" - on_connect(): Initiating chat with agent {agent} using message '{initial_msg}'",
        flush=True,
    )
    user_proxy.initiate_chat(  # noqa: F704
        agent,
        message=initial_msg,
    )

with IOWebsockets.run_server_in_thread(on_connect=on_connect, port=8765) as uri:
    print(f" - test_setup() with websocket server running on {uri}.", flush=True)

    with ws_connect(uri) as websocket:
        print(f" - Connected to server on {uri}", flush=True)

        print(" - Sending message to server.", flush=True)
        # websocket.send("2+2=?")
        websocket.send("Check out the weather in Shanghai and 并写一段Python的冒泡排序算法，以及一段测试websocket的例子，必须要包含各种容错和代码注释.")

        while True:
            message = websocket.recv()
            message = message.decode("utf-8") if isinstance(message, bytes) else message
            print("cjr websocket.start...........")
            print(message, end="", flush=True)
            print("cjr websocket.end...........")

            if "TERMINATE" in message:
                print()
                print(" - Received TERMINATE message. Exiting.", flush=True)
                break
