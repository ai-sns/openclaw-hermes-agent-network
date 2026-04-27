from langchain.chat_models import init_chat_model  
from deepagents import create_deep_agent  
from deepagents.backends.filesystem import FilesystemBackend
  
# 创建本地 shell backend  
backend = FilesystemBackend(  
    root_dir="C:/Users/IDD/Documents",  
    virtual_mode=True  
)
  
# 创建带自定义 base_url 的模型  
model = init_chat_model(  
    "openai:gpt-4o",  
    base_url="https://api.chatanywhere.tech/v1",  
    api_key="sk-SVCuk9EAqrgUEvvh31PKxVIr1fZhwt5boDB2Hexw8vs2Bl26"  # 可选  
)  
  
# 使用配置好的模型创建 agent  
agent = create_deep_agent(model=model,backend=backend)  
  
# 正常调用，base_url 已经配置在模型中  
result = agent.invoke({  
    "messages": [{"role": "user", "content": "List files in / and read the joke txt file"}]  
})
print(result)