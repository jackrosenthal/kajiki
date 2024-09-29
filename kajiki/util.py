import os.path
from collections import deque
from random import randint
from threading import local


def expose(func):
    func.exposed = True
    return func


class flattener:  # noqa: N801
    def __init__(self, iterator):
        while type(iterator) == flattener:
            iterator = iterator.iterator
        self.iterator = iterator

    @classmethod
    def decorate(cls, func):
        def inner(*args, **kwargs):
            return cls(func(*args, **kwargs))

        return inner

    def accumulate_str(self):
        if type(self.iterator) == flattener:
            return self.iterator.accumulate_str()
        s = ""
        iter_stack = [self.iterator]
        while iter_stack:
            try:
                x = next(iter_stack[-1])
            except StopIteration:
                iter_stack.pop()
                continue
            if type(x) == flattener:
                iter_stack.append(x.iterator)
            elif x is None:
                pass
            else:
                s += x
        return s

    def __iter__(self):
        for x in self.iterator:
            if type(x) == flattener:
                for xx in x:
                    if xx is not None:
                        yield xx
            elif x is not None:
                yield x


def literal(text):
    return flattener(iter([text]))


class NameGen:
    lcl = local()

    def __init__(self):
        self.names = set()

    @classmethod
    def gen(cls, hint):
        if not hasattr(cls.lcl, "inst"):
            cls.lcl.inst = NameGen()
        return cls.lcl.inst._gen(hint)  # noqa: SLF001

    def _gen(self, hint):
        r = hint
        while r in self.names:
            r = "%s_%d" % (hint, randint(0, len(self.names) * 10))  # noqa: S311
        self.names.add(r)
        return r


def gen_name(hint="_kj_"):
    return NameGen.gen(hint)


def window(seq, n=2):
    """Return a sliding window of size ``n`` over an iterator"""
    win = deque((next(seq, None) for _ in range(n)), maxlen=n)
    yield win
    for item in seq:
        win.append(item)
        yield win


def default_alias_for(name):
    return os.path.splitext(os.path.basename(name))[0]
