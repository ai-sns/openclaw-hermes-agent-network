import os
import time
from fastapi import FastAPI
from autogenstudio.teammanager import TeamManager

app = FastAPI()
team_manager = TeamManager()


def convert_to_openai_format(result_message):
    messages = result_message.task_result.messages

    assistant_msg = None
    for msg in reversed(messages):
        if msg.source != "user":
            content = getattr(msg, "content", None)
            if content and content != "TERMINATE":
                assistant_msg = content
                break

    prompt_tokens = 0
    completion_tokens = 0

    for msg in messages:
        usage = getattr(msg, "models_usage", None)
        if usage:
            prompt_tokens += usage.prompt_tokens or 0
            completion_tokens += usage.completion_tokens or 0

    return {
        "id": "chatcmpl-autogen",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "autogen-team",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": assistant_msg or ""
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        }
    }


@app.get("/predict/{task}")
async def predict(task: str):
    try:
        team_file_path = os.environ.get("AUTOGENSTUDIO_TEAM_FILE")

        if team_file_path is None:
            raise ValueError("AUTOGENSTUDIO_TEAM_FILE not set")

        result_message = await team_manager.run(
            task=task,
            team_config=team_file_path
        )

        return convert_to_openai_format(result_message)

    except Exception as e:
        return {
            "error": {
                "message": str(e),
                "type": "server_error"
            }
        }

if __name__ == "__main__":
    import uvicorn
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--team", type=str, required=True)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    # 设置环境变量（你代码里用到了）
    os.environ["AUTOGENSTUDIO_TEAM_FILE"] = args.team

    print(f"🚀 Starting server on port {args.port}")
    print(f"📄 Using team config: {args.team}")

    uvicorn.run(
        "autogenapi:app",   # 文件名:app变量
        host="0.0.0.0",
        port=args.port,
        reload=False
    )