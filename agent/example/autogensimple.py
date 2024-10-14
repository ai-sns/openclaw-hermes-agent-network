from typing import Union, List

from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen import oai


def print_message_before_send(sender,message, recipient, silent):
    #参数都在相应的hooklist处理事件中传进来
    print("cjrok---print_message_before_send---")
    hm=input("你要发送什么？")
    print("我要发送：",message)
    return message

def print_last_received_message(content: Union[str, List[dict]]):
    # 参数都在相应的hooklist处理事件中传进来
    print("cjrok---print_last_received_message---")
    hm = input("你最后收到什么？")
    print("我最后收到：",content)
    return content

def print_all_messages_before_reply(content: Union[str, List[dict]]):
    # 参数都在相应的hooklist处理事件中传进来
    print("cjrok---print_all_messages_before_reply---")
    hm = input("收到的全部信息是什么？")
    print("我全部收到：",content)
    return content

def print_message_before_sendassistant(sender,message, recipient, silent):
    #参数都在相应的hooklist处理事件中传进来
    print("assistantcjrok---print_message_before_send---")
    hm=input("你要发送什么？")
    print("我assistant要发送：",message)
    return message

def print_last_received_messageassistant(content: Union[str, List[dict]]):
    # 参数都在相应的hooklist处理事件中传进来
    print("assistantcjrok---print_last_received_message---")
    hm = input("你最后收到什么？")
    print("我assistant最后收到：",content)
    return content

def print_all_messages_before_replyassistant(content: Union[str, List[dict]]):
    # 参数都在相应的hooklist处理事件中传进来
    print("assistantcjrok---print_all_messages_before_reply---")
    hm = input("收到的全部信息是什么？")
    print("我assistant全部收到：",content)
    return content



def main():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    # config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    config_list = {"model": "gpt-4o", "api_key": "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", "seed": 42, "temperature": 0,"stream":True}

    # Create the agent that uses the LLM.
    assistant = ConversableAgent("agent", llm_config=config_list)

    # Create the agent that represents the user in the conversation.
    user_proxy = UserProxyAgent("user", code_execution_config=False)

    assistant.register_hook(hookable_method="process_message_before_send", hook=print_message_before_sendassistant)
    assistant.register_hook(hookable_method="process_last_received_message", hook=print_last_received_messageassistant)
    assistant.register_hook(hookable_method="process_all_messages_before_reply", hook=print_all_messages_before_replyassistant)

    user_proxy.register_hook(hookable_method="process_message_before_send", hook=print_message_before_send)
    user_proxy.register_hook(hookable_method="process_last_received_message", hook=print_last_received_message)
    user_proxy.register_hook(hookable_method="process_all_messages_before_reply", hook=print_all_messages_before_reply)


    # Let the assistant start the conversation.  It will end when the user types exit.
    user_proxy.initiate_chat(assistant, message="你是谁?")
    # assistant.initiate_chat(user_proxy, message="你是谁?")


if __name__ == "__main__":
    main()
