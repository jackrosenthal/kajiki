import sys
from threading import local

def debug():
    def pm(etype, value, tb): # pragma no cover
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

    def __iter__(self):
        for x in self.iterator:
            if isinstance(x, flattener):
                for xx in x:
                    yield xx
            else:
                yield x

class TLProxy(object):

    def __init__(self, factory):
        self._factory = factory
        self._local = local()

    def _get(self):
        try:
            result = self._local.value
        except AttributeError:
            result = self._local.value = self.factory()
        return result

    def __getattr__(self, name):
        return getattr(self._get(), name)
