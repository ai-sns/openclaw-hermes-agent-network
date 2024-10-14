# filename: draw_characters_v2.py
import turtle

def draw_donald_duck():
    turtle.speed(1)
    
    # Draw head
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.color('white')
    turtle.begin_fill()
    turtle.circle(100)  # Head
    turtle.end_fill()

    # Draw beak
    turtle.color('orange')
    turtle.penup()
    turtle.goto(-30, -50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.setheading(30)
    turtle.circle(30, 180)  # Beak
    turtle.end_fill()

    # Draw eyes
    turtle.penup()
    turtle.goto(-35, 20)
    turtle.pendown()
    turtle.color('black')
    turtle.begin_fill()
    turtle.circle(15)  # Left eye
    turtle.end_fill()

    turtle.penup()
    turtle.goto(35, 20)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(15)  # Right eye
    turtle.end_fill()

    # Draw pupils
    turtle.color('white')
    turtle.penup()
    turtle.goto(-35, 25)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Left pupil
    turtle.end_fill()

    turtle.penup()
    turtle.goto(35, 25)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Right pupil
    turtle.end_fill()

    # Draw hat
    turtle.penup()
    turtle.goto(-50, 60)
    turtle.pendown()
    turtle.color('blue')
    turtle.begin_fill()
    turtle.setheading(0)
    turtle.circle(50, 180)
    turtle.end_fill()

def draw_mickey_mouse():
    turtle.speed(1)

    # Draw head
    turtle.penup()
    turtle.goto(200, -50)
    turtle.pendown()
    turtle.color('black')
    turtle.begin_fill()
    turtle.circle(100)  # Head
    turtle.end_fill()

    # Draw ears
    turtle.penup()
    turtle.goto(120, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(50)  # Left ear
    turtle.end_fill()

    turtle.penup()
    turtle.goto(280, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(50)  # Right ear
    turtle.end_fill()

    # Draw eyes
    turtle.penup()
    turtle.goto(165, 10)
    turtle.pendown()
    turtle.color('white')
    turtle.begin_fill()
    turtle.circle(15)  # Left eye
    turtle.end_fill()

    turtle.penup()
    turtle.goto(235, 10)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(15)  # Right eye
    turtle.end_fill()

    # Draw pupils
    turtle.color('black')
    turtle.penup()
    turtle.goto(165, 15)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Left pupil
    turtle.end_fill()

    turtle.penup()
    turtle.goto(235, 15)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Right pupil
    turtle.end_fill()

    # Draw mouth
    turtle.penup()
    turtle.goto(175, -30)
    turtle.pendown()
    turtle.setheading(-60)
    turtle.circle(20, 120)  # Mouth

# Set up the screen
turtle.reset()
draw_donald_duck()
draw_mickey_mouse()

# Finish
turtle.done()