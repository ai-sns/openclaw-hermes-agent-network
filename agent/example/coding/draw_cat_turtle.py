# filename: draw_cat_turtle.py
import turtle

def draw_cat():
    # Set up the turtle
    turtle.speed(1)

    # Draw the cat's face
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.circle(100)  # face

    # Draw the eyes
    turtle.penup()
    turtle.goto(-35, 25)
    turtle.pendown()
    turtle.dot(30, "black")  # left eye

    turtle.penup()
    turtle.goto(35, 25)
    turtle.pendown()
    turtle.dot(30, "black")  # right eye

    # Draw the nose
    turtle.penup()
    turtle.goto(0, 10)
    turtle.pendown()
    turtle.dot(20, "pink")  # nose

    # Draw the mouth
    turtle.penup()
    turtle.goto(-20, -10)
    turtle.pendown()
    turtle.goto(0, -30)
    turtle.goto(20, -10)

    # Draw the ears
    turtle.penup()
    turtle.goto(-100, 50)
    turtle.pendown()
    turtle.goto(-60, 100)
    turtle.goto(-20, 50)

    turtle.penup()
    turtle.goto(100, 50)
    turtle.pendown()
    turtle.goto(60, 100)
    turtle.goto(20, 50)

    turtle.hideturtle()  # Hide the turtle
    turtle.done()  # Finish the drawing

draw_cat()