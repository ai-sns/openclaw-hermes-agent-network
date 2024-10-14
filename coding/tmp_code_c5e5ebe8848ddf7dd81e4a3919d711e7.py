import turtle

def draw_circle(color, x, y, radius):
    turtle.penup()
    turtle.fillcolor(color)
    turtle.goto(x, y)
    turtle.pendown()
    turtle.begin_fill()
    turtle.circle(radius)
    turtle.end_fill()

def draw_eye(color, x, y, radius):
    draw_circle(color, x, y, radius)

def draw_nose(color, x, y, radius):
    draw_circle(color, x, y, radius)

# 设置窗口
turtle.setup(500, 500)
turtle.speed(10)
turtle.bgcolor("white")

# 画脸
draw_circle("#c19a6b", 0, -50, 100)  # 脸

# 画眼睛
draw_eye("black", -35, 35, 35)  # 左眼
draw_eye("black", 35, 35, 35)   # 右眼

# 画鼻子
draw_nose("black", 0, -10, 10)   # 鼻子

# 画嘴巴
turtle.penup()
turtle.goto(-15, -50)
turtle.pendown()
turtle.setheading(-60)
turtle.circle(15, 120)

# 隐藏turtle
turtle.hideturtle()

# 结束绘画
turtle.done()