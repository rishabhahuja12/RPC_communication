import math


def add(args):
    return args[0] + args[1]


def factorial(args):
    return math.factorial(args[0])


def reverse(args):
    return args[0][::-1]


TASK_HANDLERS = {
    "add": add,
    "factorial": factorial,
    "reverse": reverse,
}
