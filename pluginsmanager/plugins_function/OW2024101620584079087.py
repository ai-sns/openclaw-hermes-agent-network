def bubble_sort(arr):
    """
    冒泡排序算法实现
    :param arr: 待排序的列表
    :return: 排序后的列表
    """
    n = len(arr)  # 获取列表的长度
    # 外层循环控制排序次数
    for i in range(n):
        # 设置一个标志位，用于检测是否发生了交换
        swapped = False
        # 内层循环进行相邻元素的比较与交换
        for j in range(0, n - i - 1):
            # 如果当前元素大于下一个元素，则交换它们
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]  # 交换
                swapped = True  # 发生了交换
        # 如果没有发生交换，说明列表已经有序，可以提前结束
        if not swapped:
            break
    return arr

# 测试冒泡排序算法
if __name__ == "__main__":
    sample_list = [64, 34, 25, 12, 22, 11, 90]
    sorted_list = bubble_sort(sample_list)
    print("排序后的列表:", sorted_list)
