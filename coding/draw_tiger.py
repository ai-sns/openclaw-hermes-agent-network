# filename: draw_tiger.py
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
    
    turtle.hideturtle()
    turtle.done()

draw_tiger()