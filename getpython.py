import re

text = """
冒泡排序是一种简单的排序算法，它重复地遍历要排序的数列，每次遍历时通过比较相邻两个元素的大小，将较大（或较小）的元素交换到数列的末尾。下面是使用 Python 语言实现冒泡排序算法的示例代码：

```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        # 外层循环控制遍历次数
        for j in range(n - i - 1):
            # 内层循环控制每次比较次数
            if arr[j] > arr[j + 1]:
                # 如果当前元素大于下一个元素，交换它们的位置
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

arr = [64, 34, 25, 12, 22, 11, 90]
sorted_arr = bubble_sort(arr)
print("排序后的数组是：")
for i in range(len(sorted_arr)):
    print("%d" % sorted_arr[i], end=" ")
```
这个有什么左右呢，cjrok

```python
def cjrfunction(arr):
    n = len(arra)
    for i in range(naa):
        # 外层循环控制遍历次数aaa
```
it iis a duplicate
```python
def cjrfunction(arr):
    n = len(arra)
    for i in range(naa):
        # 外层循环控制遍历次数aaa
```
"""

# 使用正则表达式提取Python代码块
python_code_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
python_code_matches = python_code_pattern.findall(text)

# 打印提取的Python代码块
python_code_list = []

for code_block in python_code_matches:
    python_code_list.append(code_block.strip())

# 打印结果
print("Python代码列表:")
i=0
s=text

answer_list = []
for code in python_code_list:
    print("i:",i)
    print(code)

    substring = code
    left_part = s[:s.find(substring)]
    right_part = s[s.find(substring) + len(substring):]
    print("左边所有字符:", left_part)
    print("右边所有字符:", right_part)


    left_part = left_part[:left_part.find("```python")]
    right_part = right_part[right_part.find("```") + len("```"):]
    s = right_part
    answer_list.append(left_part)
    answer_list.append(code)


    i+=1


print("show all list *************************")
j=0
for answer in answer_list:
    print("*******",j,"***********")
    print(answer)
    j+=1
