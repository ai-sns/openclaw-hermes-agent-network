# filename: draw_full_tiger.py
import turtle

def draw_tiger():
    turtle.speed(5)

    # Draw head
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(100)
    turtle.end_fill()

    # Draw eyes
    turtle.penup()
    turtle.goto(-35, 35)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(35, 35)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()

    # Draw pupils
    turtle.penup()
    turtle.goto(-35, 40)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(5)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(35, 40)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)
    turtle.end_fill()

    # Draw nose
    turtle.penup()
    turtle.goto(0, 10)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(10)
    turtle.end_fill()

    # Draw mouth
    turtle.penup()
    turtle.goto(-20, -20)
    turtle.pendown()
    turtle.right(90)
    turtle.circle(20, 180)

    turtle.penup()
    turtle.goto(20, -20)
    turtle.pendown()
    turtle.right(180)
    turtle.circle(20, -180)

    # Draw body
    turtle.penup()
    turtle.goto(-70, -150)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.setheading(-60)
    turtle.circle(100, 120)
    turtle.setheading(0)
    turtle.forward(140)
    turtle.setheading(60)
    turtle.circle(100, 120)
    turtle.end_fill()

    # Draw tail
    turtle.penup()
    turtle.goto(-70, -150)
    turtle.pendown()
    turtle.color("orange")
    turtle.setheading(-30)
    turtle.begin_fill()
    turtle.circle(60, 60)  # Tail curve
    turtle.setheading(30)
    turtle.circle(-60, 60)  # Tail back
    turtle.end_fill()

    turtle.hideturtle()
    turtle.done()

draw_tiger()