# filename: draw_with_matplotlib.py
import matplotlib.pyplot as plt
import numpy as np

def draw_square():
    # Create a square
    square = plt.Rectangle((0, 0), 1, 1, color='blue')
    plt.gca().add_patch(square)
    plt.xlim(-0.5, 1.5)
    plt.ylim(-0.5, 1.5)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title("Simple Square")
    plt.show()

def main():
    print("Drawing a square with Matplotlib...")
    draw_square()
    print("Finished drawing.")

if __name__ == "__main__":
    main()