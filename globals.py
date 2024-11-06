# 所有的agent列表
global_agent_list = {}
# 载入所有的插件
global_plugin_list = {}
# 获取当前的联系人列表，用于自动调用ai进行聊天
global_buddy_list = {}

global_env = {"lang": 1}
# lang,0:英文，1为中文
llm_ability = ['理解能力', '总结能力', '知识面', '逻辑推理', '数学计算',
               '代码编程', '创作写作文档', '附件能力', '图文识别能力',
               '图片生成能力', '视频识别能力', '视频生成能力', '搜索能力']

question_num = 3
question_type=llm_ability[0]
question_prompt='''
    请生成question_num个问题，这些问题旨在评估用户的question_type。问题应该涉及不同的主题，包括但不限于语言理解、逻辑推理、数学问题解决和常识判断。每个问题不需要答案。以下是问题生成的格式要求：

1. 问题：[问题描述]
2. 问题：[问题描述]
 ...
'''

question_speed='''
    请解释“破釜沉舟”这个成语的意思，并给出一个使用该成语的例句。
'''
