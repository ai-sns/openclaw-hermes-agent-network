# plugin_interface.py
class PluginInterface:
    def create_widget(self, *args, **kwagrs):
        raise NotImplementedError("Plugins must implement the create_widget method.")

    def sent_message_handle(self, *args, **kwagrs):
        raise NotImplementedError("Plugins must implement the sent_message_handle method.")

    def received_message_handle(self, *args, **kwagrs):
        raise NotImplementedError("Plugins must implement the received_message_handle method.")
