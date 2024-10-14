# filename: draw_characters.py
import turtle

def draw_mickey():
    turtle.penup()
    turtle.goto(-50, 0)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(50)  # Head
    turtle.end_fill()
    turtle.penup()
    turtle.goto(-100, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(30)  # Left ear
    turtle.end_fill()
    turtle.penup()
    turtle.goto(0, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(30)  # Right ear
    turtle.end_fill()
    turtle.penup()
    turtle.goto(-30, -15)
    turtle.color("white")
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(15)  # Face
    turtle.end_fill()

def draw_donald():
    turtle.penup()
    turtle.goto(100, -50)
    turtle.pendown()
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(50)  # Body
    turtle.end_fill()
    turtle.penup()
    turtle.goto(100, 0)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(30)  # Head
    turtle.end_fill()
    turtle.penup()
    turtle.goto(120, 5)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(10)  # Eye
    turtle.end_fill()
    turtle.penup()
    turtle.goto(80, 5)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(10)  # Eye
    turtle.end_fill()
    turtle.penup()
    turtle.goto(100, -10)
    turtle.color("orange")
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(15)  # Beak
    turtle.end_fill()

def main():
    turtle.speed(1)
    draw_mickey()
    draw_donald()
    turtle.done()  # Keep the window open

if __name__ == "__main__":
    main()