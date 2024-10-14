import turtle

def draw_donald_duck():
    # Drawing 唐老鸭 (Donald Duck)
    turtle.penup()
    turtle.goto(-50, 0)
    turtle.pendown()
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(50)  # Head
    turtle.end_fill()

    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(30)  # Eye
    turtle.end_fill()

    turtle.penup()
    turtle.goto(-70, 10)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(5)  # Eye pupil
    turtle.end_fill()

    turtle.penup()
    turtle.goto(-30, 10)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Eye pupil
    turtle.end_fill()

    turtle.penup()
    turtle.goto(-50, -50)
    turtle.pendown()
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(25)  # Beak
    turtle.end_fill()

def draw_mickey_mouse():
    # Drawing 米老鼠 (Mickey Mouse)
    turtle.penup()
    turtle.goto(100, 0)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(50)  # Head
    turtle.end_fill()

    turtle.penup()
    turtle.goto(50, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(30)  # Right Ear
    turtle.end_fill()

    turtle.penup()
    turtle.goto(150, 50)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(30)  # Left Ear
    turtle.end_fill()

    turtle.penup()
    turtle.goto(100, -20)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(20)  # Face
    turtle.end_fill()

    turtle.penup()
    turtle.goto(90, -10)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(5)  # Left Eye
    turtle.end_fill()

    turtle.penup()
    turtle.goto(110, -10)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(5)  # Right Eye
    turtle.end_fill()

    turtle.penup()
    turtle.goto(100, -15)
    turtle.pendown()
    turtle.color("red")
    turtle.begin_fill()
    turtle.circle(10)  # Nose
    turtle.end_fill()

# Setup turtle environment
turtle.speed(3)

draw_donald_duck()
draw_mickey_mouse()

turtle.hideturtle()
turtle.done()