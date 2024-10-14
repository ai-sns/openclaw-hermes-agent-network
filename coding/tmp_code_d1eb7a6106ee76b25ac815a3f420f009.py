def my_function():
    b = 3
    globals_dict = {}
    locals_dict = {"b",b}

    # 使用 exec()，并指定 globals 和 locals
    exec("c = b + 2", globals_dict, locals_dict)

    # b 在 locals_dict 中
    print(locals_dict['c'])  # 输出: 5  (b + 2 = 3 + 2)

my_function()