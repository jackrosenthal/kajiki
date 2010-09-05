import types

from .util import flattener, UNDEFINED

class Runtime(object):

    def __init__(self, context):
        self.context = context

    def bind(self, func):
        return TplFunc(func, self.context)

    def extends(self, child, parent):
        symbols = parent.symbols
        symbols.update(
            (k,v) for k,v in child.symbols.iteritems()
            if k != '__call__')
        
        parent_context = Context(self.context.current)
        child_context = Context(self.context.current)
        bound_parent = BoundTemplate(parent, parent_context)
        bound_child = BoundTemplate(parent, child_context)
        

        child_context.current['parent'] = bound_parent
        parent_context.current['child'] = bound_child
                                 
        context = Context(self.context.current)
        context.current.update(
            (name, TplFunc(value, context))
            for name, value in symbols.iteritems())
        return context['__call__']()

class Context(object):

    def __init__(self, *args, **kwargs):
        self.current = dict(*args, **kwargs)
        self['__builtins__'] = __builtins__
        self['__fpt__'] = Runtime(self)

    def __getitem__(self, name):
        return self.current.get(name, UNDEFINED)

    def __setitem__(self, name, value):
        self.current[name] = value

    def bind(self, func):
        return TplFunc(func, self)

class TplFunc(object):
    __slots__ = ('func')

    def __init__(self, func_obj, context):
        func = types.FunctionType(func_obj.func_code, context.current)
        self.func = func
    
    def __call__(self, *args, **kwargs):
        return flattener(self.func(*args, **kwargs))

class BoundTemplate(object):

    def __init__(self, template, context):
        self._template = template
        self._ftbl = dict(
            (name, TplFunc(value, context))
            for name, value in template.symbols.iteritems())
        
    def __getattr__(self, name):
        return self._ftbl.get(name, UNDEFINED)

