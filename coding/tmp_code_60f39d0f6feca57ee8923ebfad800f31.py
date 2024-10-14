import turtle

# 创建一个画笔
pen = turtle.Turtle()
pen.speed(1)

# 画猫的头
pen.fillcolor('lightgrey')
pen.begin_fill()
pen.circle(100)  # 画一个圆形作为猫的头
pen.end_fill()

# 画猫的耳朵
pen.fillcolor('grey')
pen.begin_fill()
pen.goto(-100, 100)
pen.goto(-60, 200)
pen.goto(-20, 100)
pen.end_fill()

pen.begin_fill()
pen.goto(100, 100)
pen.goto(60, 200)
pen.goto(20, 100)
pen.end_fill()

# 画猫的眼睛
pen.penup()
pen.goto(-35, 40)
pen.pendown()
pen.fillcolor('white')
pen.begin_fill()
pen.circle(15)  # 左眼
pen.end_fill()

pen.penup()
pen.goto(35, 40)
pen.pendown()
pen.fillcolor('white')
pen.begin_fill()
pen.circle(15)  # 右眼
pen.end_fill()

# 画猫的瞳孔
pen.penup()
pen.goto(-35, 45)
pen.pendown()
pen.fillcolor('black')
pen.begin_fill()
pen.circle(7)  # 左瞳孔
pen.end_fill()

pen.penup()
pen.goto(35, 45)
pen.pendown()
pen.fillcolor('black')
pen.begin_fill()
pen.circle(7)  # 右瞳孔
pen.end_fill()

# 画猫的鼻子
pen.penup()
pen.goto(0, 30)
pen.pendown()
pen.fillcolor('pink')
pen.begin_fill()
pen.circle(10)  # 鼻子
pen.end_fill()

# 画猫的嘴
pen.penup()
pen.goto(-10, 20)
pen.pendown()
pen.right(90)
pen.circle(10, 180)  # 左边的嘴
pen.penup()
pen.goto(10, 20)
pen.pendown()
pen.circle(-10, 180)  # 右边的嘴

# 完成绘画
pen.hideturtle()
turtle.done()