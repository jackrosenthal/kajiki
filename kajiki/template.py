import types
from cStringIO import StringIO
from cgi import escape
from functools import update_wrapper
from pprint import pprint

from webhelpers.html import literal

import kajiki
from .util import flattener

class _obj(object):
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self,k,v)

class _Template(object):
    __methods__=()
    loader = None
    base_globals = None

    def __init__(self, context=None):
        if context is None: context = {}
        self._context = context
        base_globals = self.base_globals or {}
        self.__globals__ = dict(
            base_globals,
            local=self,
            self=self,
            literal=literal,
            __builtins__=__builtins__,
            __kj__=kajiki)
        for k,v in self.__methods__:
            v = v.bind_instance(self)
            setattr(self, k, v)
            self.__globals__[k] = v
        self.__kj__ = _obj(
            render=self._render,
            extend=self._extend,
            push_switch=self._push_switch,
            pop_switch=self._pop_switch,
            case=self._case,
            import_=self._import,
            escape=self._escape,
            iter_attrs=self._iter_attrs)
        self._switch_stack = []
        self.__globals__.update(context)

    def __iter__(self):
        for chunk in self.__call__():
            yield unicode(chunk)

    def _render(self):
        try:
            return u''.join(self)
        except:
            for i, line in enumerate(self.py_text.splitlines()):
                print '%3d %s' % (i+1, line)
            raise

    def _extend(self, parent):
        if isinstance(parent, basestring):
            parent = self.loader.import_(parent)
        p_inst = parent(self._context)
        p_globals = p_inst.__globals__
        # Find overrides
        for k,v in self.__globals__.iteritems():
            if k == '__call__': continue
            if not isinstance(v, TplFunc): continue
            p_globals[k] = v
        # Find inherited funcs
        for k, v in p_inst.__globals__.iteritems():
            if k == '__call__': continue
            if not isinstance(v, TplFunc): continue
            if k not in self.__globals__: 
                self.__globals__[k] = v
            if not hasattr(self, k):
                def _(k=k):
                    '''Capture the 'k' variable in a closure'''
                    def trampoline(*a, **kw):
                        global parent
                        return getattr(parent, k)(*a, **kw)
                    return trampoline
                setattr(self, k, TplFunc(_()).bind_instance(self))
        p_globals['child'] = self
        p_globals['local'] = p_inst
        p_globals['self'] = self.__globals__['self']
        self.__globals__['parent'] = p_inst
        self.__globals__['local'] = self
        return p_inst

    def _push_switch(self, expr):
        self._switch_stack.append(expr)

    def _pop_switch(self):
        self._switch_stack.pop()

    def _case(self, obj):
        return obj == self._switch_stack[-1]

    def _import(self, name, alias, gbls):
        tpl_cls = self.loader.import_(name)
        if alias is None:
            alias = self.loader.default_alias_for(name)
        r = gbls[alias] = tpl_cls(gbls)
        return r

    def _escape(self, value):
        if isinstance(value, flattener):
            return u''.join(value) # assume flattener results are already escaped
        if hasattr(value, '__html__'):
            return value.__html__()
        else:
            return escape(unicode(value))

    def _iter_attrs(self, attrs):
        if hasattr(attrs, 'items'):
            attrs = attrs.items()
        for k,v in attrs:
            yield k, self._escape(v)

def Template(ns):
    dct = {}
    methods = dct['__methods__'] = []
    for name in dir(ns):
        value = getattr(ns, name)
        if getattr(value, 'exposed', False):
            methods.append((name, TplFunc(value.im_func)))
    return type(ns.__name__,(_Template,), dct)

def from_ir(ir_node):
    py_text = '\n'.join(map(str, ir_node.py()))
    dct = dict(kajiki=kajiki)
    try:
        exec py_text in dct
    except SyntaxError: # pragma no cover
        for i, line in enumerate(py_text.splitlines()):
            print '%3d %s' % (i+1, line)
        raise
    tpl = dct['template']
    tpl.base_globals = dct
    tpl.py_text = py_text
    return tpl

class TplFunc(object):

    def __init__(self, func, inst=None):
        self._func = func
        self._inst = inst
        self._bound_func = None

    def bind_instance(self, inst):
        return TplFunc(self._func, inst)

    def __repr__(self): # pragma no cover
        if self._inst:
            return '<bound tpl_function %r of %r>' % (
                self._func.func_name, self._inst)
        else:
            return '<unbound tpl_function %r>' % (self._func.func_name)

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
