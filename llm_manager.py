from globals import global_plugin_list
from db.DBFactory import add_PluginMng, query_PluginMng_All, query_PluginMng, update_PluginMng, delete_PluginMng



def get_all_llm_record():
    records = query_PluginMng_All(plugin_type="LLM_Connector")
    return records


def get_all_llm_connector_list():
    """
    获取所有 LLM 连接器的名称列表。

    :return: 包含所有 LLM 连接器名称的列表。
    """
    # 查询所有插件管理中的 LLM 连接器记录
    records = query_PluginMng_All(plugin_type="LLM_Connector")

    # 使用列表推导式优化生成 LLM 连接器名称列表
    llm_list = [record.name for record in records]

    return llm_list

def get_llm_plugin_by_name(name):
    plugin = global_plugin_list[f"{name}"]
    return plugin

def get_llm_config_by_name(name):
    llm_plugin=get_llm_plugin_by_name(name)
    config = llm_plugin.get_config()
    return config

def get_plugin_cfg_by_name(name):
    llm_plugin=get_llm_plugin_by_name(name)
    config = llm_plugin.get_plugin_cfg()
    return config

def get_all_llm_model_list():
    """
    获取所有 LLM 连接器的模型列表。

    :return: 包含所有 LLM 连接器及其模型名称的列表。
    """
    # 获取所有 LLM 连接器的名称列表
    connector_list = get_all_llm_connector_list()

    all_model_list = []

    # 遍历每个连接器，提取模型类型并构建模型名称
    for connector_name in connector_list:
        # 获取插件配置
        plugin_cfg = get_plugin_cfg_by_name(connector_name)
        model_type = plugin_cfg.get('model_type', None)

        # 如果 model_type 不为 None，则进行分割并构建模型名称
        if model_type:
            model_list = model_type.split(",")
            # 使用列表推导式构建模型名称
            all_model_list.extend(f"{connector_name}:{model_name.strip()}" for model_name in model_list)

    return all_model_list

def get_model_type_list_by_connector_name(connector_name):

        plugin_cfg = get_plugin_cfg_by_name(connector_name)
        model_type = plugin_cfg.get('model_type', None)

        model_list = model_type.split(",")

        stripped_model_list = [element.strip() for element in model_list]


        return stripped_model_list
