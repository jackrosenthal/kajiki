import types
from functools import update_wrapper
from pprint import pprint

from .util import flattener

class _Template(object):

    def __init__(self, context):
        self._context = context

    def __iter__(self):
        for chunk in self():
            yield unicode(chunk)

    def render(self):
        return u''.join(self)

    def extend(self, parent):
        child = self.__class__
        # Generate a new template instance
        parent_context = dict(self._context.top())
        child_context = dict(self._context.top())
        child_symbols = dict(
            (k, v.bind_context(child_context))
            for k,v in child.__symbols__.iteritems()
            if isinstance(v, TplFunc)
            and k != '__call__')
        parent_symbols = dict(
            (k, v.bind_context(parent_context))
            for k,v in parent.__symbols__.iteritems()
            if isinstance(v, TplFunc))
        symbols = dict(parent_symbols)
        symbols.update(child_symbols)
        derived = type(child.__name__, (_Template,), dict(__symbols__=symbols))
        derived_inst = derived(None)
        for k,v in symbols.iteritems():
            setattr(derived_inst, k, v)
            parent_context[k] = child_context[k] = v
        print dir(derived_inst)
        return derived_inst

def Template(ns):
    dct = {}
    dct['__symbols__'] = dct
    for name in dir(ns):
        value = getattr(ns, name)
        if getattr(value, 'exposed', False):
            dct[name] = TplFunc(value.im_func)
    return type(ns.__name__,(_Template,), dct)

class TplFunc(object):

    def __init__(self, func):
        self._func = func

    def __get__(self, inst, cls=None):
        if inst:
            d = dict(inst._context.top(),
                     __builtins__=__builtins__,
                     self=inst)
            # pprint(inst.__symbols__)
            d.update((k, v.bind_context(d))
                     for k,v in inst.__symbols__.iteritems()
                     if isinstance(v, TplFunc))
            return self.bind_context(d)
        else:
            return self._func

    def bind_context(self, context):
        func = types.FunctionType(
            self._func.func_code,
            context,
            self._func.func_name,
            self._func.func_defaults,
            self._func.func_closure
            )
        return update_wrapper(
            lambda *a,**kw:flattener(func(*a,**kw)),
            func)
