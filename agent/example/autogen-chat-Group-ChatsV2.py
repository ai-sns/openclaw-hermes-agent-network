import os
import sys

sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")
from autogen import ConversableAgent
from Agent import Agent,AgentsCommander

llm_config_mng={"config_list": [{"model": "gpt-4", "api_key": "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"}],"cache_seed":None}
llm_config={"config_list": [{"model": "gpt-4o-mini", "api_key": "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"}],"cache_seed":None}
# The Number Agent always returns the same numbers.
# gpt4最快6轮，gpt4o要10轮

number_agent = Agent(
    agent_cfg = None,
    name="Number_Agent",
    system_message="You return me the numbers I give you, one number each line.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

# The Adder Agent adds 1 to each number it receives.
adder_agent = Agent(
    agent_cfg = None,
    name="Adder_Agent",
    system_message="You add 1 to each number I give you and return me the new numbers, one number each line.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

# The Multiplier Agent multiplies each number it receives by 2.
multiplier_agent = Agent(
    agent_cfg = None,
    name="Multiplier_Agent",
    system_message="You multiply each number I give you by 2 and return me the new numbers, one number each line.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

# The Subtracter Agent subtracts 1 from each number it receives.
subtracter_agent = Agent(
    agent_cfg = None,
    name="Subtracter_Agent",
    system_message="You subtract 1 from each number I give you and return me the new numbers, one number each line.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

# The Divider Agent divides each number it receives by 2.
divider_agent = Agent(
    agent_cfg = None,
    name="Divider_Agent",
    system_message="You divide each number I give you by 2 and return me the new numbers, one number each line.",
    llm_config=llm_config,
    human_input_mode="NEVER",
)
# The `description` attribute is a string that describes the agent.
# It can also be set in `ConversableAgent` constructor.
adder_agent.description = "Add 1 to each input number."
multiplier_agent.description = "Multiply each input number by 2."
subtracter_agent.description = "Subtract 1 from each input number."
divider_agent.description = "Divide each input number by 2."
number_agent.description = "Return the numbers given."

from autogen import GroupChat

group_chat = GroupChat(
    agents=[adder_agent, multiplier_agent, subtracter_agent, divider_agent, number_agent],
    messages=[],
    max_round=6,
    speaker_selection_method="auto"

)

from autogen import GroupChatManager

group_chat_manager = AgentsCommander(
    groupchat=group_chat,
    llm_config=llm_config_mng,
)
chat_result = number_agent.initiate_chat(
    group_chat_manager,
    message="My number is 3, I want to turn it into 13.",
    # message="陆六过失伤人，作为辩护律师有哪些事情需要处理",
    summary_method="reflection_with_llm",
)
