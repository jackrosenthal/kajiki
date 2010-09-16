import sys
from random import randint
from threading import local

from webhelpers.html import literal

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
        self.iterator = iterator

    @classmethod
    def decorate(cls, func):
        def inner(*args, **kwargs):
            return cls(func(*args, **kwargs))
        return inner

    def __iter__(self):
        for x in self.iterator:
            if isinstance(x, flattener):
                for xx in x:
                    yield xx
            else:
                yield x

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

def gen_name(hint='_fpt_'):
    return NameGen.gen(hint)
    
