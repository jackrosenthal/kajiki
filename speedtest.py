import sys
from collections import defaultdict
import time

from contextlib import contextmanager
from fastpt import Template
from genshi.template import MarkupTemplate

FN='fastpt/tests/perf/tables.html'

timings = defaultdict(float)

@contextmanager
def timing(s):
    start = time.time()
    yield
    elapsed = time.time() - start
    print '%s: %s s' % (s, elapsed)
    timings[s] += elapsed

with timing('compile.fastpt'):
    fpt = Template(FN)
    fpt.compile()
with timing('compile.genshi'):
    gt = MarkupTemplate(open(FN))
with timing('render.100.fastpt'):
    fpt.render(size=100)
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.100.fastpt'):
    fpt.render(size=100)
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.100.fastpt'):
    fpt.render(size=100)
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.500.fastpt'):
    fpt.render(size=500)
with timing('render.500.genshi'):
    gt.generate(size=500).render()
print 'Compile fastpt speedup: %s' % (
    timings['compile.genshi'] / timings['compile.fastpt'])
print 'Render 100 fastpt speedup: %s' % (
    timings['render.100.genshi'] / timings['render.100.fastpt'])
print 'Render 500 fastpt speedup: %s' % (
    timings['render.500.genshi'] / timings['render.500.fastpt'])


