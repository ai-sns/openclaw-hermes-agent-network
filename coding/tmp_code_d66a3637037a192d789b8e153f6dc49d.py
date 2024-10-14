import turtle

# 设置画布
screen = turtle.Screen()
screen.bgcolor("white")

# 创建一个兔子对象
cat = turtle.Turtle()
cat.color("black")
cat.fillcolor("gray")
cat.speed(3)

# 画猫的身体
cat.begin_fill()
cat.circle(100)  # 身体
cat.end_fill()

# 画猫的头
cat.penup()
cat.goto(0, 100)
cat.pendown()
cat.begin_fill()
cat.circle(50)  # 头
cat.end_fill()

# 画猫的眼睛
for x in [-20, 20]:
    cat.penup()
    cat.goto(x, 120)
    cat.pendown()
    cat.color("white")
    cat.begin_fill()
    cat.circle(10)  # 眼白
    cat.end_fill()
    
    cat.color("black")
    cat.penup()
    cat.goto(x, 125)
    cat.pendown()
    cat.begin_fill()
    cat.circle(5)  # 瞳孔
    cat.end_fill()

# 画猫的耳朵
cat.penup()
cat.goto(-30, 150)
cat.pendown()
cat.fillcolor("gray")
cat.begin_fill()
cat.goto(-50, 200)
cat.goto(-10, 180)
cat.end_fill()

cat.penup()
cat.goto(30, 150)
cat.pendown()
cat.fillcolor("gray")
cat.begin_fill()
cat.goto(50, 200)
cat.goto(10, 180)
cat.end_fill()

# 画猫的嘴
cat.penup()
cat.goto(0, 110)
cat.pendown()
cat.goto(-10, 100)
cat.goto(0, 105)
cat.goto(10, 100)

# 隐藏海龟
cat.hideturtle()

# 完成绘画
turtle.done()