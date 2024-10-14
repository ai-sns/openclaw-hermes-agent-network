# filename: animated_character_basic.py
import tkinter as tk
from PIL import Image, ImageTk
import os

class AnimatedCharacter:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)  # Keep the window on top

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(script_dir, "character.gif")

        try:
            self.img = Image.open(img_path)
        except FileNotFoundError:
            print(f"Image file not found at {img_path}. Please ensure the file exists.")
            exit(1)

        # Get image dimensions
        self.img_width, self.img_height = self.img.size

        # Convert each frame to RGBA and store them as PhotoImage
        self.frames = []
        try:
            while True:
                frame_image = ImageTk.PhotoImage(self.img.copy().convert('RGBA'))
                self.frames.append(frame_image)
                self.img.seek(self.img.tell() + 1)
        except EOFError:
            pass

        self.canvas = tk.Canvas(root, width=self.img_width, height=self.img_height, highlightthickness=0)
        self.canvas.pack()
        self.img_id = self.canvas.create_image(0, 0, anchor='nw', image=self.frames[0])

        # Start the animation
        self.current_frame = 0
        self.root.after(0, self.update_frame)

    def update_frame(self):
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.canvas.itemconfig(self.img_id, image=self.frames[self.current_frame])
        self.root.after(100, self.update_frame)  # Adjust the delay for smoother animation

if __name__ == "__main__":
    root = tk.Tk()
    app = AnimatedCharacter(root)
    root.mainloop()