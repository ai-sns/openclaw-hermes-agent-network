def bubble_sort(arr):
    """
    冒泡排序算法
    :param arr: 待排序的列表
    :return: 排序后的列表
    """
    n = len(arr)  # 获取列表的长度
    
    # 外层循环控制比较的轮数
    for i in range(n):
        # 内层循环进行相邻元素的比较
        for j in range(0, n-i-1):  # 每一轮可以减少比较的次数
            # 如果当前元素大于下一个元素，交换它们
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]  # 交换操作

    return arr  # 返回排序后的列表

# 使用示例
if __name__ == "__main__":
    sample_list = [64, 34, 25, 12, 22, 11, 90]
    sorted_list = bubble_sort(sample_list)
    print("排序后的列表是:", sorted_list)