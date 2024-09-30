#!/usr/bin/env -S hatch env run -e speedtest python
# ruff: noqa: T201

import time
from collections import defaultdict
from contextlib import contextmanager

from genshi.template import MarkupTemplate

from kajiki import XMLTemplate

FN = "tests/data/tables.html"

timings = defaultdict(float)


@contextmanager
def timing(s):
    start = time.time()
    yield
    elapsed = time.time() - start
    print(f"{s}: {elapsed} s")
    timings[s] += elapsed


with timing("compile.kajiki"):
    fpt = XMLTemplate(filename=FN)
with timing("compile.genshi"), open(FN) as f:
    gt = MarkupTemplate(f)
with timing("render.100.kajiki"):
    fpt({"size": 100}).render()
with timing("render.100.genshi"):
    gt.generate(size=100).render()
with timing("render.100.kajiki"):
    fpt({"size": 100}).render()
with timing("render.100.genshi"):
    gt.generate(size=100).render()
with timing("render.100.kajiki"):
    fpt({"size": 100}).render()
with timing("render.100.genshi"):
    gt.generate(size=100).render()
with timing("render.500.kajiki"):
    fpt({"size": 500}).render()
with timing("render.500.genshi"):
    gt.generate(size=500).render()
print("Compile kajiki speedup:", timings["compile.genshi"] / timings["compile.kajiki"])
print("Render 100 kajiki speedup:", timings["render.100.genshi"] / timings["render.100.kajiki"])
print("Render 500 kajiki speedup:", timings["render.500.genshi"] / timings["render.500.kajiki"])
