from .context import Context

class Runtime(object):

    def __init__(self):
        self.context = Context()

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



    
