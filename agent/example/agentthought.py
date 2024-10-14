from langchain import OpenAI, Agent, Tool, OpenAIAgentLauncher

# 初始化OpenAI模型
llm = OpenAI(api_key='sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t')

# 定义一些工具（Tools）
tools = [
    Tool(name="search", func=print),
    Tool(name="calculator", func=print)
]

# 创建代理
agent = Agent(llm=llm, tools=tools)

# 配置代理启动器（用于启用中间思考流程输出）
launcher = OpenAIAgentLauncher(agent, verbose=True)

# 运行代理
response = launcher.run("你的问题在这里")
print(response)
