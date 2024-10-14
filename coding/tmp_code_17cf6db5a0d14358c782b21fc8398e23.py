import turtle

def draw_cat():
    # 设置画笔
    turtle.speed(5)
    turtle.pensize(2)

    # 画猫的头
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.circle(100)
    
    # 画猫的眼睛
    turtle.penup()
    turtle.goto(-40, 40)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(40, 40)
    turtle.pendown()
    turtle.color("white")
    turtle.begin_fill()
    turtle.circle(15)
    turtle.end_fill()

    # 画猫的瞳孔
    turtle.penup()
    turtle.goto(-40, 45)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(7)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(40, 45)
    turtle.pendown()
    turtle.color("black")
    turtle.begin_fill()
    turtle.circle(7)
    turtle.end_fill()

    # 画猫的鼻子
    turtle.penup()
    turtle.goto(0, 20)
    turtle.pendown()
    turtle.color("pink")
    turtle.begin_fill()
    turtle.circle(10)
    turtle.end_fill()

    # 画猫的嘴
    turtle.penup()
    turtle.goto(-10, 10)
    turtle.pendown()
    turtle.setheading(-60)
    turtle.circle(10, 120)
    
    turtle.penup()
    turtle.goto(10, 10)
    turtle.pendown()
    turtle.setheading(-120)
    turtle.circle(10, 120)

    # 画猫的耳朵
    turtle.penup()
    turtle.goto(-70, 80)
    turtle.pendown()
    turtle.setheading(100)
    turtle.begin_fill()
    turtle.goto(-30, 150)
    turtle.goto(-10, 80)
    turtle.goto(-70, 80)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(70, 80)
    turtle.pendown()
    turtle.setheading(80)
    turtle.begin_fill()
    turtle.goto(30, 150)
    turtle.goto(10, 80)
    turtle.goto(70, 80)
    turtle.end_fill()

    # 隐藏画笔
    turtle.hideturtle()
    turtle.done()

draw_cat()