# filename: draw_tiger_improved.py
import turtle

def draw_tiger():
    # Set up the turtle
    turtle.speed(5)
    turtle.bgcolor("white")
    
    # Draw head
    turtle.penup()
    turtle.goto(0, -100)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(100)
    turtle.end_fill()

    # Draw stripes
    turtle.penup()
    turtle.goto(-70, -30)
    turtle.setheading(30)
    turtle.pendown()
    turtle.color("black")
    for _ in range(3):
        turtle.forward(100)
        turtle.right(90)
        turtle.forward(10)
        turtle.right(90)
        turtle.forward(100)
        turtle.right(90)
        turtle.forward(10)
        turtle.right(90)
        turtle.penup()
        turtle.setheading(30)
        turtle.forward(20)
        turtle.pendown()

    # Draw eyes
    for x in [-35, 35]:
        turtle.penup()
        turtle.goto(x, 10)
        turtle.pendown()
        turtle.color("white")
        turtle.begin_fill()
        turtle.circle(15)
        turtle.end_fill()
        turtle.color("black")
        turtle.penup()
        turtle.goto(x, 15)
        turtle.pendown()
        turtle.begin_fill()
        turtle.circle(5)
        turtle.end_fill()

    # Draw nose
    turtle.penup()
    turtle.goto(0, -10)
    turtle.pendown()
    turtle.color("pink")
    turtle.begin_fill()
    turtle.circle(10)
    turtle.end_fill()

    # Draw mouth
    turtle.penup()
    turtle.goto(-20, -30)
    turtle.setheading(-60)
    turtle.pendown()
    turtle.circle(20, 120)

    turtle.penup()
    turtle.goto(20, -30)
    turtle.setheading(-120)
    turtle.pendown()
    turtle.circle(20, 120)

    turtle.hideturtle()
    turtle.done()

draw_tiger()