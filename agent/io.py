#IOStream处理
import sys

from autogen.io.base import IOStream
from rich.console import Console
from rich.text import Text
from typing import Any
sys.path.append("../..")
sys.path.append("../../..")
from speaker import Speaker



from typing import Union, List

class AISNSIOStream(IOStream):
    def __init__(self,speaker:Speaker):
        self.speaker =speaker


    def printbak(self, *args: Any, **kwargs) -> None:
        # Remove 'flush' argument if present, as it's not supported by rich.console.Console.print
        kwargs.pop('flush', None)
        processed_args = []
        for arg in args:
            if isinstance(arg, str):
                # Convert args with ANSI codes into rich Text objects
                processed_args.append(Text.from_ansi(arg))
            else:
                # Non-string arguments are added without modification
                processed_args.append(arg)
        print("cjr in the AISNSIOStream:"+self.prefix_str)
        self.console.print(markup=False, *processed_args, **kwargs)

    def print(self, *objects: Any, sep: str = " ", end: str = "\n", flush: bool = False) -> None:

        speaker=self.speaker
        speaker.speak(*objects, sep=sep, end=end, flush=flush)


    def input(self, prompt: str = "", *, password: bool = False) -> str:
        speaker = self.speaker
        input_str=speaker.input(prompt = prompt, password  = password)
        return input_str
