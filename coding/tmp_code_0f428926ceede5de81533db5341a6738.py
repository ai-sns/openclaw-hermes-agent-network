import turtle

# Function to draw Donald Duck
def draw_donald_duck():
    turtle.penup()
    turtle.goto(-100, -50)
    turtle.pendown()
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(50)  # Head
    turtle.end_fill()

    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(40)  # Face
    turtle.end_fill()

    turtle.penup()
    turtle.goto(-120, -40)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(10)  # Beak
    turtle.end_fill()

# Function to draw Mickey Mouse
def draw_mickey_mouse():
    turtle.penup()
    turtle.goto(100, -50)
    turtle.pendown()
    
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(50)  # Head
    turtle.end_fill()
    
    turtle.penup()
    turtle.goto(80, -10)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(30)  # Face
    turtle.end_fill()
    
    turtle.penup()
    turtle.goto(130, 0)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(20)  # Ear
    turtle.end_fill()

# Setup screen
turtle.speed(1)
turtle.bgcolor("white")

# Draw characters
draw_donald_duck()
draw_mickey_mouse()

# Complete drawing
turtle.hideturtle()
turtle.done()