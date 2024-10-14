# filename: draw_cat.py
import turtle

def draw_cat():
    # Set up the turtle
    turtle.speed(1)
    
    # Draw the head
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.circle(50)

    # Draw the eyes
    for x in [-20, 20]:
        turtle.penup()
        turtle.goto(x, 0)
        turtle.pendown()
        turtle.circle(10)

    # Draw the nose
    turtle.penup()
    turtle.goto(0, -10)
    turtle.pendown()
    turtle.circle(-5, steps=3)  # Draw a triangle

    # Draw the mouth
    turtle.penup()
    turtle.goto(0, -10)
    turtle.pendown()
    turtle.right(90)
    turtle.circle(10, 180)
    turtle.penup()
    turtle.goto(0, -10)
    turtle.pendown()
    turtle.right(360)
    turtle.circle(-10, 180)

    # Draw the ears
    for x in [-30, 30]:
        turtle.penup()
        turtle.goto(x, 50)
        turtle.pendown()
        turtle.goto(x - 20, 75)
        turtle.goto(x + 20, 50)

    # Finish up
    turtle.hideturtle()
    turtle.done()

draw_cat()