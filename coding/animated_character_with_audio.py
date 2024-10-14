# filename: animated_character_with_audio.py
import tkinter as tk
from PIL import Image, ImageTk
import random
import os
import pygame

class AnimatedCharacter:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)  # Keep the window on top

        # Initialize Pygame mixer
        pygame.mixer.init()

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(script_dir, "character.gif")
        sound_path = os.path.join(script_dir, "voice.wav")

        try:
            self.img = Image.open(img_path)
        except FileNotFoundError:
            print(f"Image file not found at {img_path}. Please ensure the file exists.")
            exit(1)

        # Load the sound file
        try:
            self.sound = pygame.mixer.Sound(sound_path)
        except FileNotFoundError:
            print(f"Sound file not found at {sound_path}. Please ensure the file exists.")
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

        self.canvas = tk.Canvas(root, width=self.img_width, height=self.img_height + 50, highlightthickness=0)
        self.canvas.pack()
        self.img_id = self.canvas.create_image(0, 0, anchor='nw', image=self.frames[0])
        self.text_id = self.canvas.create_text(self.img_width // 2, self.img_height + 25, text="你好！陈佳荣", font=("Arial", 16), fill="white")

        # Start the animation and movement
        self.current_frame = 0
        self.root.after(0, self.update_frame)
        self.move_image()
        self.play_sound()

    def update_frame(self):
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.canvas.itemconfig(self.img_id, image=self.frames[self.current_frame])
        self.root.after(100, self.update_frame)  # Adjust the delay for smoother animation

    def move_image(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        new_x = random.randint(0, screen_width - self.img_width)
        new_y = random.randint(0, screen_height - self.img_height - 50)

        self.root.geometry(f'{self.img_width}x{self.img_height + 50}+{new_x}+{new_y}')
        self.root.after(1000, self.move_image)  # Adjust the delay for movement

    def play_sound(self):
        self.sound.play()

if __name__ == "__main__":
    root = tk.Tk()
    app = AnimatedCharacter(root)
    root.mainloop()