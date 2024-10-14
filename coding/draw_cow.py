# filename: draw_cow.py
import turtle

def draw_cow():
    # Setup the turtle
    turtle.speed(1)
    turtle.bgcolor("white")

    # Draw the body
    turtle.fillcolor("white")
    turtle.begin_fill()
    turtle.circle(100)
    turtle.end_fill()

    # Draw the head
    turtle.penup()
    turtle.goto(-50, 100)
    turtle.pendown()
    turtle.fillcolor("white")
    turtle.begin_fill()
    turtle.circle(50)
    turtle.end_fill()

    # Draw the eyes
    turtle.penup()
    turtle.goto(-70, 130)
    turtle.pendown()
    turtle.dot(10, "black")

    turtle.penup()
    turtle.goto(-30, 130)
    turtle.pendown()
    turtle.dot(10, "black")

    # Draw the nose
    turtle.penup()
    turtle.goto(-50, 110)
    turtle.pendown()
    turtle.fillcolor("pink")
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()

    # Draw the ears
    turtle.penup()
    turtle.goto(-100, 130)
    turtle.pendown()
    turtle.fillcolor("white")
    turtle.begin_fill()
    turtle.setheading(45)
    turtle.circle(30, 180)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(0, 130)
    turtle.pendown()
    turtle.fillcolor("white")
    turtle.begin_fill()
    turtle.setheading(135)
    turtle.circle(30, 180)
    turtle.end_fill()

    # Complete drawing
    turtle.hideturtle()
    turtle.done()

if __name__ == "__main__":
    draw_cow()