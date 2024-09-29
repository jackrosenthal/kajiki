"""Comment copied from Python/compile.c:

All about a_lnotab.

c_lnotab is an array of unsigned bytes disguised as a Python string.
It is used to map bytecode offsets to source code line #s (when needed
for tracebacks).

The array is conceptually a list of
    (bytecode offset increment, line number increment)
pairs. The details are important and delicate, best illustrated by example:

    byte code offset   source code line number
       0                   1
       6                   2
      50                   7
     350                 307
     361                 308

The first trick is that these numbers aren't stored, only the increments
from one row to the next (this doesn't really work, but it's a start):

    0, 1,  6, 1,  44, 5,  300, 300,  11, 1

The second trick is that an unsigned byte can't hold negative values, or
values larger than 255, so (a) there's a deep assumption that byte code
offsets and their corresponding line #s both increase monotonically, and (b)
if at least one column jumps by more than 255 from one row to the next, more
than one pair is written to the table. In case #b, there's no way to know
from looking at the table later how many were written.	That's the delicate
part.  A user of c_lnotab desiring to find the source line number
corresponding to a bytecode address A should do something like this:

    lineno = addr = 0
    for addr_incr, line_incr in co_lnotab:
        addr += addr_incr
        if addr > A:
            return lineno
        if line_incr >= 0x80:
            line_incr -= 0x100
        lineno += line_incr

In order for this to work, when the addr field increments by more than 255,
the line # increment in each pair generated must be 0 until the remaining addr
increment is < 256.  So, in the example above, assemble_lnotab (it used
to be called com_set_lineno) should not (as was actually done until 2.2)
expand 300, 300 to 255, 255, 45, 45,
            but to 255,   0, 45, 255, 0, 45.
"""


def lnotab(pairs, first_lineno=0):
    """Yields byte integers representing the pairs of integers passed in."""
    assert first_lineno <= pairs[0][1]  # noqa: S101
    cur_byte, cur_line = 0, first_lineno
    for byte_off, line_off in pairs:
        byte_delta = byte_off - cur_byte
        line_delta = line_off - cur_line
        assert byte_delta >= 0  # noqa: S101
        while byte_delta > 255:  # noqa: PLR2004
            yield 255  # byte
            yield 0  # line
            byte_delta -= 255
        yield byte_delta
        while line_delta >= 0x80:  # noqa: PLR2004
            yield 0x7F  # line
            yield 0  # byte
            line_delta -= 0x7F
        while line_delta < -0x80:  # noqa: PLR2004
            yield 0x80  # line
            yield 0  # byte
            line_delta += 0x80
        if line_delta < 0:
            line_delta += 0x100
            assert 0x80 <= line_delta <= 0xFF  # noqa: S101, PLR2004
        yield line_delta
        cur_byte, cur_line = byte_off, line_off


def lnotab_string(pairs, first_lineno=0):
    return bytes(lnotab(pairs, first_lineno))
