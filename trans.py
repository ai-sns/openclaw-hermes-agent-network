import sys
from pathlib import Path

sys.path.append("..")
# sys.path.append("../..")

import importlib
from db.DBFactory import query_config_lang



class GlobalTrans:
    _lang = "zh"
    _text = {}

    def __init__(self):
        raise RuntimeError("这个类不能被实例化")

    @staticmethod
    def static_method():
        print("这是一个全局静态方法")

    @property
    def lang(cls):
        return cls._lang

    @lang.setter
    def lang(cls, value):
        cls._lang = value

    @staticmethod
    def get_lang():
        try:
            GlobalTrans._lang = query_config_lang()
        except Exception as e:
            GlobalTrans._lang = "zh"
        print("这是一个全局静态方法")

    @staticmethod
    def set_lang(value):
        try:
            GlobalTrans._lang = query_config_lang(value)
        except Exception as e:
            GlobalTrans._lang = "zh"
        print("这是一个全局静态方法")

    @staticmethod
    def tr(value, def_val=""):
        dic = GlobalTrans._text
        lst = value.split('.')
        for l in lst:
            dic = dic.get(l)
        if dic:
            return dic
        return def_val

    @staticmethod
    def set_text():
        dict_name = "__lantxt"
        module_name = "lang.zh.lang_zh"
        if GlobalTrans.lang == "zh":
            module_name = "lang.zh.lang_zh"
        elif GlobalTrans.lang == "en":
            module_name = "lang.en.lang_en"
        module = importlib.import_module(module_name)
        lang = getattr(module, dict_name)
        # print(lang)
        GlobalTrans._text = lang

        # 使用全局静态类的方法
# GlobalStaticClass.static_method()
