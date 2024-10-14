# filename: test_turtle.py
import turtle

def draw_square():
    turtle.color("blue")
    turtle.begin_fill()
    for _ in range(4):
        turtle.forward(100)
        turtle.right(90)
    turtle.end_fill()

def main():
    print("Starting turtle graphics...")
    turtle.speed(1)
    draw_square()
    turtle.done()  # Keep the window open
    print("Finished drawing.")

if __name__ == "__main__":
    main()