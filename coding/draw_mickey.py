# filename: draw_mickey.py
import turtle

def draw_circle(color, radius, x, y):
    turtle.penup()
    turtle.fillcolor(color)
    turtle.goto(x, y)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(radius)
    turtle.end_fill()

def draw_mickey():
    turtle.speed(5)

    # Draw the head
    draw_circle("black", 100, 0, -100)

    # Draw the left ear
    draw_circle("black", 50, -120, 0)

    # Draw the right ear
    draw_circle("black", 50, 120, 0)

    # Draw the face
    draw_circle("white", 80, 0, -80)

    # Draw the eyes
    draw_circle("black", 12, -35, -60)
    draw_circle("black", 12, 35, -60)

    # Draw the pupils
    draw_circle("white", 5, -35, -57)
    draw_circle("white", 5, 35, -57)

    # Draw the nose
    draw_circle("black", 15, 0, -40)

    # Draw the mouth
    turtle.penup()
    turtle.goto(-40, -50)
    turtle.pendown()
    turtle.setheading(-60)
    turtle.circle(40, 120)

    turtle.hideturtle()
    turtle.done()

draw_mickey()