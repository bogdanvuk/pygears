from functools import reduce


def divide(seq, length):
    return [seq[i: i+length] for i in range(0, len(seq), length)]


def oper_tree(din, func):
    pairs = divide(din, 2)
    results = []
    for i in pairs:
        if(len(i) == 2):
            results.append(func(*i))
        else:
            results.append(i)

    return func(*results)


def oper_reduce(din, func, init=0):
    return reduce(func, din, init)
