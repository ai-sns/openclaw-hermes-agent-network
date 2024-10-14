import turtle

# 创建画布和turtle对象
screen = turtle.Screen()
cat = turtle.Turtle()

# 画猫的头
cat.color("black")
cat.penup()
cat.goto(-50, 0) # 设置起始位置
cat.pendown()
cat.circle(40) # 画猫的头

# 画猫的身体
cat.penup()
cat.goto(-50, -30)
cat.pendown()
cat.right(90)
cat.forward(100) # 画猫的身体

# 画猫的左腿
cat.penup()
cat.goto(-90, -30)
cat.pendown()
cat.right(180)
cat.forward(50)

# 画猫的右腿
cat.penup()
cat.goto(10, -30)
cat.pendown()
cat.forward(50)

# 画猫的尾巴
cat.penup()
cat.goto(-20, -100)
cat.pendown()
cat.right(45)
cat.forward(100)

# 画猫的左耳
cat.penup()
cat.goto(-70, 40)
cat.pendown()
cat.left(90)
cat.forward(30)
cat.left(90)
cat.forward(10)

# 画猫的右耳
cat.penup()
cat.goto(-30, 40)
cat.pendown()
cat.left(90)
cat.forward(30)
cat.left(90)
cat.forward(10)

# 隐藏turtle
cat.hideturtle()

# 结束
screen.mainloop()