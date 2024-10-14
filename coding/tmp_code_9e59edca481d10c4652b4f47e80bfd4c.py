import turtle

def draw_cat():
    # 创建画布
    screen = turtle.Screen()
    screen.bgcolor("white")

    # 创建一个海龟
    cat = turtle.Turtle()
    cat.color("black")
    cat.pensize(3)

    # 画猫的头
    cat.penup()
    cat.goto(0, -50)
    cat.pendown()
    cat.circle(50)

    # 画猫的耳朵
    cat.penup()
    cat.goto(-50, 0)
    cat.pendown()
    cat.goto(-80, 50)
    cat.goto(-50, 30)

    cat.penup()
    cat.goto(50, 0)
    cat.pendown()
    cat.goto(80, 50)
    cat.goto(50, 30)

    # 画猫的眼睛
    cat.penup()
    cat.goto(-20, -20)
    cat.pendown()
    cat.circle(5)

    cat.penup()
    cat.goto(20, -20)
    cat.pendown()
    cat.circle(5)

    # 画猫的鼻子
    cat.penup()
    cat.goto(0, -30)
    cat.pendown()
    cat.circle(5)

    # 画猫的嘴
    cat.penup()
    cat.goto(0, -35)
    cat.pendown()
    cat.goto(-10, -45)
    cat.goto(0, -40)
    cat.goto(10, -45)

    # 完成
    cat.hideturtle()
    turtle.done()

draw_cat()