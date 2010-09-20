import types
from cStringIO import StringIO
from cgi import escape
from functools import update_wrapper
from pprint import pprint

from webhelpers.html import literal

import kajiki
from .util import flattener
from .html_utils import HTML_EMPTY_ATTRS
from . import lnotab

class _obj(object):
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self,k,v)

class _Template(object):
    __methods__=()
    loader = None
    base_globals = None
    filename = None

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
            extend=self._extend,
            push_switch=self._push_switch,
            pop_switch=self._pop_switch,
            case=self._case,
            import_=self._import,
            escape=self._escape,
            render_attrs=self._render_attrs)
        self._switch_stack = []
        self.__globals__.update(context)

    def __iter__(self):
        for chunk in self.__main__():
            yield unicode(chunk)

    def render(self):
        # return self.__main__()
        return self.__main__().accumulate_str()

    def _extend(self, parent):
        if isinstance(parent, basestring):
            parent = self.loader.import_(parent)
        p_inst = parent(self._context)
        p_globals = p_inst.__globals__
        # Find overrides
        for k,v in self.__globals__.iteritems():
            if k == '__main__': continue
            if not isinstance(v, TplFunc): continue
            p_globals[k] = v
        # Find inherited funcs
        for k, v in p_inst.__globals__.iteritems():
            if k == '__main__': continue
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
        if type(value) == flattener:
            return value
        if hasattr(value, '__html__'):
            return value.__html__()
        else:
            return escape(unicode(value))

    def _render_attrs(self, attrs, mode):
        if hasattr(attrs, 'items'):
            attrs = attrs.items()
        for k,v in attrs:
            if v is None: continue
            if mode.startswith('html') and k in HTML_EMPTY_ATTRS: yield ' '+k.upper()
            else: yield ' %s="%s"' % (k,self._escape(v))

    @classmethod
    def annotate_lnotab(cls, py_to_tpl):
        for name, meth in cls.__methods__:
            meth.annotate_lnotab(cls.filename, py_to_tpl, dict(py_to_tpl))

def Template(ns):
    dct = {}
    methods = dct['__methods__'] = []
    for name in dir(ns):
        value = getattr(ns, name)
        if getattr(value, 'exposed', False):
            methods.append((name, TplFunc(value.im_func)))
    return type(ns.__name__,(_Template,), dct)

def from_ir(ir_node):
    py_lines = list(ir_node.py())
    py_text = '\n'.join(map(str, py_lines))
    py_linenos = [ ]
    last_lineno = 0
    for i,l in enumerate(py_lines):
        lno =max(last_lineno, l._lineno or 0)
        py_linenos.append((i+1, lno))
        last_lineno = lno
    dct = dict(kajiki=kajiki)
    try:
        exec py_text in dct
    except (SyntaxError, IndentationError), err: # pragma no cover
        for i, line in enumerate(py_text.splitlines()):
            print '%3d %s' % (i+1, line)
        raise
    tpl = dct['template']
    tpl.base_globals = dct
    tpl.py_text = py_text
    tpl.filename = ir_node.filename
    tpl.annotate_lnotab(py_linenos)
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

    def annotate_lnotab(self, filename, py_to_tpl, py_to_tpl_dct):
        if not py_to_tpl: return
        code = self._func.func_code
        new_lnotab_numbers = []
        for bc_off, py_lno in lnotab.lnotab_numbers(code.co_lnotab, code.co_firstlineno):
            tpl_lno = py_to_tpl_dct.get(py_lno, None)
            if tpl_lno is None:
                print 'ERROR LOOKING UP LINE #%d' % py_lno
                continue
            new_lnotab_numbers.append((bc_off, tpl_lno))
        if not new_lnotab_numbers: return
        new_firstlineno = py_to_tpl_dct.get(code.co_firstlineno, 0)
        new_lnotab = lnotab.lnotab_string(new_lnotab_numbers, new_firstlineno)
        new_code = types.CodeType(
            code.co_argcount,
            code.co_nlocals,
            code.co_stacksize,
            code.co_flags,
            code.co_code,
            code.co_consts,
            code.co_names,
            code.co_varnames,
            filename.encode('utf-8'),
            code.co_name,
            new_firstlineno,
            new_lnotab,
            code.co_freevars,
            code.co_cellvars)
        self._func.func_code = new_code
        return

