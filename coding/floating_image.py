# filename: floating_image.py

import tkinter as tk
from PIL import Image, ImageTk
import random
import os

class FloatingImage:
    def __init__(self, image_path):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # 去掉窗口装饰
        self.root.attributes('-topmost', True)  # 窗口置于顶层

        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)
        
        self.label = tk.Label(self.root, image=self.tk_image, bd=0)
        self.label.pack()

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        self.root.after(0, self.update_position)
        self.root.attributes('-alpha', 1.0)  # 显示窗口
        self.root.mainloop()
    
    def update_position(self):
        x = random.randint(0, self.screen_width - self.image.width)
        y = random.randint(0, self.screen_height - self.image.height)
        self.root.geometry(f"+{x}+{y}")
        self.root.after(1000, self.update_position)

if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_directory, "person.png")
    FloatingImage(image_path)