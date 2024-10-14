# filename: draw_donald_duck_v2.py
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
    
    # Face
    draw_circle('white', 0, 0, 100)  # Face
    draw_circle('black', -30, 40, 20)  # Left eye
    draw_circle('black', 30, 40, 20)   # Right eye
    draw_circle('white', -30, 40, 10)  # Left eye white
    draw_circle('white', 30, 40, 10)   # Right eye white
    
    # Beak
    turtle.penup()
    turtle.goto(-40, -10)
    turtle.pendown()
    turtle.fillcolor('orange')
    turtle.begin_fill()
    turtle.setheading(0)
    turtle.circle(40, 180)
    turtle.setheading(-90)
    turtle.forward(20)
    turtle.setheading(180)
    turtle.circle(-40, 180)
    turtle.setheading(90)
    turtle.forward(20)
    turtle.end_fill()
    
    # Hat
    turtle.penup()
    turtle.goto(-40, 80)
    turtle.pendown()
    turtle.fillcolor('blue')
    turtle.begin_fill()
    turtle.setheading(0)
    turtle.forward(80)
    turtle.setheading(90)
    turtle.forward(20)
    turtle.setheading(180)
    turtle.forward(80)
    turtle.setheading(270)
    turtle.forward(20)
    turtle.end_fill()
    
    turtle.penup()
    turtle.goto(-50, 80)
    turtle.pendown()
    turtle.fillcolor('white')
    turtle.begin_fill()
    turtle.setheading(0)
    turtle.forward(100)
    turtle.setheading(90)
    turtle.forward(10)
    turtle.setheading(180)
    turtle.forward(100)
    turtle.setheading(270)
    turtle.forward(10)
    turtle.end_fill()

    turtle.hideturtle()
    turtle.done()

draw_donald_duck()