#!/usr/bin/env python3
"""Write the IDNA tables at the end of src/punyidna.nv.

Three tables, each a string constant of big-endian entries, which is
how unicode-nv carries its own:

  UTS46  the IDNA Mapping Table of UTS #46, from the `idna` package's
         `uts46data` (BSD-3-Clause, Copyright (c) 2013-2025 Kim
         Davies and contributors).  One 8-byte entry per range: the
         first code point in 3 bytes, the status letter (V, M, D, I or
         X) in 1, the offset of the replacement in REPL in 3, and the
         replacement's length in code points in 1.  REPL holds the
         replacements, 3 bytes per code point.
  BIDI   the Bidi_Class of every code point, from Python's
         `unicodedata`, as ranges: 3 bytes of first code point and 1
         byte of class, numbered as BIDI_CLASSES lists them.
  JOIN   the Joining_Type RFC 5892 appendix A.1 reads, from the
         `idna` package's `idnadata.joining_types`, as ranges of 3
         bytes and 1 byte of type: 0 none, 1 C, 2 D, 3 L, 4 R, 5 T.
  SCRIPT the five scripts RFC 5892 appendix A's CONTEXTO rules name,
         from `idnadata.scripts`, as ranges: 0 other, 1 Greek,
         2 Hebrew, 3 Hiragana, 4 Katakana, 5 Han.

Everything from the line `// The IDNA tables.` to the end of
src/punyidna.nv is replaced.  The script prints each table's size;
tests/differential_tests.nv checks the mapping table against the
`idna` package's copy at 2000 code points.

Run from the package root, with the `idna` package installed:
    python3 tools/idna_tables.py
"""
import sys
import unicodedata

import idna
from idna import idnadata, uts46data

MARK = '// The IDNA tables.'
TARGET = 'src/punyidna.nv'
BIDI_CLASSES = ['L', 'R', 'AL', 'EN', 'ES', 'ET', 'AN', 'CS', 'NSM', 'BN', 'B', 'S',
                'WS', 'ON', 'LRE', 'LRO', 'RLE', 'RLO', 'PDF', 'LRI', 'RLI', 'FSI', 'PDI']
JOIN_TYPES = {'C': 1, 'D': 2, 'L': 3, 'R': 4, 'T': 5}
SCRIPTS = {'Greek': 1, 'Hebrew': 2, 'Hiragana': 3, 'Katakana': 4, 'Han': 5}


def be(n, width):
    return bytes((n >> (8 * (width - 1 - k))) & 0xFF for k in range(width))


def literal(data):
    return '"' + ''.join('\\x%02X' % b for b in data) + '"'


def ranges_of(value_at):
    """Covering ranges of a per-code-point value: (start, value) pairs."""
    out = []
    last = None
    for cp in range(0x110000):
        v = value_at(cp)
        if v != last:
            out.append((cp, v))
            last = v
    return out


def from_intranges(table, codes):
    """A covering function from idna's packed (start << 32 | end) ranges."""
    spans = []
    for name, code in codes.items():
        for packed in table[name]:
            spans.append((packed >> 32, packed & 0xFFFFFFFF, code))
    spans.sort()
    lookup = {}
    for lo, hi, code in spans:
        for cp in range(lo, hi):
            lookup[cp] = code
    return lambda cp: lookup.get(cp, 0)


def main():
    entries, repl = bytearray(), bytearray()
    count = 0
    for start, status, replacement in zip(uts46data.uts46_starts, uts46data.uts46_statuses,
                                           uts46data.uts46_replacements):
        cps = [ord(c) for c in (replacement or '')]
        entries += be(start, 3) + bytes([status]) + be(len(repl) // 3, 3) + bytes([len(cps)])
        for c in cps:
            repl += be(c, 3)
        count += 1
    bidi = ranges_of(lambda cp: BIDI_CLASSES.index(unicodedata.bidirectional(chr(cp)) or 'L'))
    join_at = from_intranges(idnadata.joining_types, JOIN_TYPES)
    join = ranges_of(join_at)
    script_at = from_intranges(idnadata.scripts, SCRIPTS)
    script = ranges_of(script_at)

    def table(ranges):
        out = bytearray()
        for cp, v in ranges:
            out += be(cp, 3) + bytes([v])
        return out

    lines = [MARK, '//',
             '// Written by tools/idna_tables.py: the IDNA Mapping Table of UTS #46',
             '// version %s from the `idna` package %s, and the Bidi_Class of' % (uts46data.__version__, idna.__version__),
             '// Unicode %s.  Each constant is a run of big-endian entries, and' % unicodedata.unidata_version,
             '// the script says what each field is.', '',
             'const TABLE_VERSION: Str = "%s"' % uts46data.__version__,
             'const BIDI_VERSION: Str = "%s"' % unicodedata.unidata_version,
             'const UTS46_ENTRIES: Int = %d' % count,
             'const UTS46: Str = %s' % literal(entries),
             'const REPL: Str = %s' % literal(repl),
             'const BIDI_ENTRIES: Int = %d' % len(bidi),
             'const BIDI: Str = %s' % literal(table(bidi)),
             'const JOIN_ENTRIES: Int = %d' % len(join),
             'const JOIN: Str = %s' % literal(table(join)),
             'const SCRIPT_ENTRIES: Int = %d' % len(script),
             'const SCRIPT: Str = %s' % literal(table(script)), '']
    src = open(TARGET).read()
    head = src[:src.index(MARK)] if MARK in src else src.rstrip('\n') + '\n\n'
    open(TARGET, 'w').write(head + '\n'.join(lines))
    print('uts46 %d entries, %d replacement code points; bidi %d; join %d; script %d'
          % (count, len(repl) // 3, len(bidi), len(join), len(script)))


if __name__ == '__main__':
    main()
