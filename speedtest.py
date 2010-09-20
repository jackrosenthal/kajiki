import sys
from collections import defaultdict
import time

from contextlib import contextmanager
from kajiki import XMLTemplate
from genshi.template import MarkupTemplate

FN='kajiki/perf/tables.html'

timings = defaultdict(float)

@contextmanager
def timing(s):
    start = time.time()
    yield
    elapsed = time.time() - start
    print '%s: %s s' % (s, elapsed)
    timings[s] += elapsed

with timing('compile.kajiki'):
    fpt = XMLTemplate(filename=FN)
    # fpt.compile()
with timing('compile.genshi'):
    gt = MarkupTemplate(open(FN))
with timing('render.100.kajiki'):
    fpt(dict(size=100)).render()
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.100.kajiki'):
    fpt(dict(size=100)).render()
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.100.kajiki'):
    fpt(dict(size=100)).render()
with timing('render.100.genshi'):
    gt.generate(size=100).render()
with timing('render.500.kajiki'):
    fpt(dict(size=500)).render()
with timing('render.500.genshi'):
    gt.generate(size=500).render()
print 'Compile kajiki speedup: %s' % (
    timings['compile.genshi'] / timings['compile.kajiki'])
print 'Render 100 kajiki speedup: %s' % (
    timings['render.100.genshi'] / timings['render.100.kajiki'])
print 'Render 500 kajiki speedup: %s' % (
    timings['render.500.genshi'] / timings['render.500.kajiki'])


