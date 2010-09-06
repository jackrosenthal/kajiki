import types
from functools import update_wrapper
from pprint import pprint

import fastpt
from .util import flattener

class _obj(object):
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self,k,v)

class _Template(object):
    __methods__=()

    def __init__(self, context=None):
        if context is None: context = {}
        self._context = context
        self.__globals__ = dict(
            context,
            local=self,
            self=self,
            __builtins__=__builtins__,
            __fpt__=fastpt.v2)
        for k,v in self.__methods__:
            v.bind_instance(self)
            setattr(self, k, v)
            self.__globals__[k] = v
        self.__fpt__ = _obj(
            render=self._render,
            extend=self._extend)

    def __iter__(self):
        for chunk in self.__call__():
            yield unicode(chunk)

    def _render(self):
        return u''.join(self)

    def _extend(self, parent):
        p_inst = parent(self._context)
        d_inst = parent(self._context)
        p_globals = p_inst.__globals__
        d_globals = d_inst.__globals__
        # Override methods from child
        for k,v in self.__methods__:
            if k == '__call__': continue
            v = getattr(self, k)
            setattr(d_inst, k, v)
            d_globals[k] = v
        p_globals['child'] = d_globals['child'] = self 
        d_globals['self'] = self.__globals__['self']
        d_globals['local'] = p_inst
        self.__globals__.setdefault('parent', p_inst)
        return d_inst

def Template(ns):
    dct = {}
    methods = dct['__methods__'] = []
    for name in dir(ns):
        value = getattr(ns, name)
        if getattr(value, 'exposed', False):
            methods.append((name, TplFunc(value.im_func)))
    return type(ns.__name__,(_Template,), dct)

class TplFunc(object):

    def __init__(self, func):
        self._func = func
        self._inst = None
        self._bound_func = None

    def bind_instance(self, inst):
        self._inst = inst

    def __call__(self, *args, **kwargs):
        if self._bound_func is None:
            self._bound_func = self._bind_globals(
                self._inst.__globals__)
        return self._bound_func(*args, **kwargs)

    def _bind_globals(self, globals):
        '''Return a function which has the globals dict set to 'globals' and which
        flattens the result of self._func'.
        '''
        func = types.FunctionType(
            self._func.func_code,
            globals,
            self._func.func_name,
            self._func.func_defaults,
            self._func.func_closure
            )
        return update_wrapper(
            lambda *a,**kw:flattener(func(*a,**kw)),
            func)
