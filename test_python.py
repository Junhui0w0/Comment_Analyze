def func():
    for i in range(10):
        if i == 6:
            return i
        print('hi')
    return 100

a = func()
print(a)