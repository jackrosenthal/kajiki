import time

from contextlib import contextmanager
from fastpt import Template
from genshi.template import MarkupTemplate

FN='fastpt/tests/perf/tables.html'

@contextmanager
def timing(s):
    start = time.time()
    yield
    elapsed = time.time() - start
    print '%s: %s s' % (s, elapsed)

with timing('fastpt compile'):
    fpt = Template(FN)
    fpt.compile()
with timing('genshi compile'):
    gt = MarkupTemplate(open(FN))
with timing('fastpt render'):
    fpt.render()
with timing('genshi render'):
    gt.generate().render()
