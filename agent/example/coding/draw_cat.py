# filename: draw_cat.py
import turtle

def draw_cat():
    # Set up turtle
    turtle.speed(3)

    # Draw head
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.circle(100)

    # Draw eyes
    turtle.penup()
    turtle.goto(-35, 25)
    turtle.pendown()
    turtle.circle(10)

    turtle.penup()
    turtle.goto(35, 25)
    turtle.pendown()
    turtle.circle(10)

    # Draw nose
    turtle.penup()
    turtle.goto(0, 10)
    turtle.pendown()
    turtle.circle(5)

    # Draw mouth
    turtle.penup()
    turtle.goto(0, 10)
    turtle.pendown()
    turtle.goto(-10, -10)
    turtle.goto(10, -10)

    # Finish
    turtle.hideturtle()
    turtle.done()

draw_cat()