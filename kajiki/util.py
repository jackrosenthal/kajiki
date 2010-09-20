import sys
from random import randint
from threading import local

def debug():# pragma no cover
    def pm(etype, value, tb): 
        import pdb, traceback
        try:
            from IPython.ipapi import make_session; make_session()
            from IPython.Debugger import Pdb
            sys.stderr.write('Entering post-mortem IPDB shell\n')
            p = Pdb(color_scheme='Linux')
            p.reset()
            p.setup(None, tb)
            p.print_stack_trace()
            sys.stderr.write('%s: %s\n' % ( etype, value))
            p.cmdloop()
            p.forget()
            # p.interaction(None, tb)
        except ImportError:
            sys.stderr.write('Entering post-mortem PDB shell\n')
            traceback.print_exception(etype, value, tb)
            pdb.post_mortem(tb)
    sys.excepthook = pm

def expose(func):
    func.exposed = True
    return func

class Undefined(object): pass
UNDEFINED=Undefined()

class flattener(object):

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
        s = u''
        iter_stack = [ self.iterator ]
        while iter_stack:
            try:
                x = iter_stack[-1].next()
            except StopIteration:
                iter_stack.pop()
                continue
            if type(x) == flattener:
                iter_stack.append(x.iterator)
            else:
                s += x
        return s

    def __iter__(self):
        for x in self.iterator:
            if type(x) == flattener:
                for xx in x:
                    yield xx
            else:
                yield x

def literal(text):
    return flattener(iter([text]))

class NameGen(object):
    lcl = local()
    def __init__(self):
        self.names = set()

    @classmethod
    def gen(cls, hint):
        if not hasattr(cls.lcl, 'inst'):
            cls.lcl.inst = NameGen()
        return cls.lcl.inst._gen(hint)

    def _gen(self, hint):
        r = hint
        while r in self.names:
            r = '%s_%d' % (hint, randint(0, 999))
        self.names.add(r)
        return r

def gen_name(hint='_kj_'):
    return NameGen.gen(hint)
    
