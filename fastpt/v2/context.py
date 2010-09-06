from .util import UNDEFINED

class Context(object):

    def __init__(self, *args, **kwargs):
        from fastpt import v2 as _fpt
        self._stack = [ dict(
                _frame=(self, 0),
                _fpt=_fpt) ]
        self.stack_push(*args, **kwargs)

    def stack_push(self, *args, **kwargs):
        next = dict(
            self.top(),
            _frame=(self, len(self._stack)))
        next.update(*args, **kwargs)
        self._stack.append(next)

    def stack_pop(self):
        self._stack.pop()

    def top(self):
        return self._stack[-1]

    def getframe(self, i):
        return self._stack[i]

    def __getitem__(self, name):
        return self.top().get(name, UNDEFINED)

    def __setitem__(self, name, value):
        self.top()[name] = value

    def update(self, *args, **kwargs):
        self.top().update(*args, **kwargs)
