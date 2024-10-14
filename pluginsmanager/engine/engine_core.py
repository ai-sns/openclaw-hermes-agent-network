import sys
from logging import Logger

from ..usecase import PluginUseCase
from ..util import LogUtil
sys.path.append("..")
sys.path.append("../..")
from globals import global_plugin_list


class PluginEngine:
    _logger: Logger

    def __init__(self, **args) -> None:
        self._logger = LogUtil.create(args['options']['log_level'])
        self.use_case = PluginUseCase(args['options'])

    def start(self) -> None:
        self.__reload_plugins()
        return self.__invoke_on_plugins('Q')

    def __reload_plugins(self) -> None:
        """Reset the list of all plugins and initiate the walk over the main
        provided plugin package to load all available plugins
        """
        self.use_case.discover_plugins(True)

    def __invoke_on_plugins(self, command: chr):
        """Apply all of the plugins on the argument supplied to this function
        """
        for module in self.use_case.modules:
            plugin = self.use_case.register_plugin(module, self._logger)
            delegate = self.use_case.hook_plugin(plugin)
            print("go meta:",plugin.meta)
            global_plugin_list[str(plugin.meta)]=delegate
            # if str(plugin.meta)=="Jiuzhou yfd Chatglm Connector: 1.0.0":
            #     print("it is jiuzhou connector")
            #     return delegate
            # elif str(plugin.meta)=="Baichuan2-13B Connector: 1.0.0":
            #     print("it is baichuan connector")
            #     # return delegate
            # else:
            #     print("not jiuzhou")
            #     print(str(plugin.meta))
            #     print("Jiuzhou yfd Chatglm Connector: 1.0.0")
            #     print(plugin.meta=="Jiuzhou yfd Chatglm Connector: 1.0.0")



            # device = delegate(command=command)
            # self._logger.info(f'Loaded device: {device}')

        return None
