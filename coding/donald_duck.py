# filename: donald_duck.py
import turtle

def draw_circle(color, x, y, radius):
    turtle.penup()
    turtle.fillcolor(color)
    turtle.goto(x, y)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(radius)
    turtle.end_fill()

def draw_donald_duck():
    turtle.speed(3)

    # Head
    draw_circle("blue", 0, -20, 100)  # Head

    # Face
    draw_circle("white", 0, 0, 80)   # Face
    draw_circle("black", -35, 30, 20) # Left eye
    draw_circle("black", 35, 30, 20)  # Right eye
    draw_circle("white", -35, 30, 10) # Left eye white
    draw_circle("white", 35, 30, 10)  # Right eye white

    # Beak
    turtle.penup()
    turtle.goto(-30, -10)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.setheading(-60)
    turtle.circle(30, 120)
    turtle.setheading(0)
    turtle.forward(60)
    turtle.setheading(120)
    turtle.circle(30, 120)
    turtle.end_fill()

    # Hat
    draw_circle("blue", 0, 60, 70)   # Hat base
    draw_circle("white", 0, 70, 55)  # Hat top

    turtle.hideturtle()
    turtle.done()

draw_donald_duck()