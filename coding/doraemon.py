# filename: doraemon.py
import turtle

def draw_doraemon():
    turtle.speed(5)
    
    # Draw face
    turtle.penup()
    turtle.goto(0, -150)
    turtle.pendown()
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(150)
    turtle.end_fill()
    
    # Draw white face
    turtle.penup()
    turtle.goto(0, -120)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(120)
    turtle.end_fill()
    
    # Draw eyes
    turtle.penup()
    turtle.goto(-50, 30)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(20)
    turtle.end_fill()
    
    turtle.penup()
    turtle.goto(50, 30)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(20)
    turtle.end_fill()
    
    # Draw pupils
    turtle.penup()
    turtle.goto(-50, 35)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(10)
    turtle.end_fill()
    
    turtle.penup()
    turtle.goto(50, 35)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(10)
    turtle.end_fill()
    
    # Draw nose
    turtle.penup()
    turtle.goto(0, 0)
    turtle.pendown()
    turtle.color("red")
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()
    
    # Draw mouth
    turtle.penup()
    turtle.goto(-40, -20)
    turtle.pendown()
    turtle.right(90)
    turtle.circle(40, 180)
    
    # Draw collar
    turtle.penup()
    turtle.goto(-60, -20)
    turtle.pendown()
    turtle.color("red")
    turtle.begin_fill()
    turtle.goto(60, -20)
    turtle.goto(40, -50)
    turtle.goto(-40, -50)
    turtle.goto(-60, -20)
    turtle.end_fill()
    
    turtle.hideturtle()
    turtle.done()

draw_doraemon()