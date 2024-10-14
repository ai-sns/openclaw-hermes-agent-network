import os

from autogen import ConversableAgent

agent = ConversableAgent(
    "chatbot",
    llm_config={"config_list": [{"model": "gpt-3.5-turbo", "api_key": "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"}]},
    code_execution_config=False,  # Turn off code execution, by default it is off.
    function_map=None,  # No registered functions, by default it is None.
    human_input_mode="NEVER",  # Never ask for human input.
)
msg="""
给我解释一下下面这句话
docker run --gpus all -it -p 8009:8009 -v ~/trans:/trans backend:v1 bash -c "cd /trans/ && 
bash 10091.sh"
"""

reply = agent.generate_reply(messages=[{"content": msg, "role": "user"}])
print(reply)
