# filename: static_image_test.py
import tkinter as tk
from PIL import Image, ImageTk
import os

def main():
    root = tk.Tk()
    root.overrideredirect(True)  # Remove window border
    root.attributes('-topmost', True)  # Keep the window on top

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(script_dir, "character.gif")

    try:
        img = Image.open(img_path)
    except FileNotFoundError:
        print(f"Image file not found at {img_path}. Please ensure the file exists.")
        exit(1)

    img_width, img_height = img.size

    # Convert image to PhotoImage
    img_tk = ImageTk.PhotoImage(img)

    canvas = tk.Canvas(root, width=img_width, height=img_height, highlightthickness=0)
    canvas.pack()
    canvas.create_image(0, 0, anchor='nw', image=img_tk)

    root.geometry(f'{img_width}x{img_height}+100+100')  # Initial position
    root.mainloop()

if __name__ == "__main__":
    main()