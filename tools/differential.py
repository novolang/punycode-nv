#!/usr/bin/env python3
"""Write tests/differential_tests.nv from two second opinions.

Punycode is checked against Python's own `punycode` codec, the RFC 3492
implementation in the standard library, over seeded strings drawn from
ASCII, Latin, Greek, Cyrillic, Arabic, Devanagari, Han, Hangul and the
astral planes.

UTS #46 is checked against the `idna` package (BSD-3-Clause), over
seeded domains built from words in several scripts.  `idna.encode`
applies the IDNA2008 code point classes on top of UTS #46, which is
stricter than UTS #46 alone, so a domain is kept only when `idna`
accepts it, and this package's `strict()` processing, which turns on
the STD3 rules and the hyphen checks as `idna` does, must give the same
ASCII.  `idna.decode` gives the Unicode form each ASCII name must come
back to.

The mapping table itself is checked at 2000 seeded code points across
every plane, the status `punyidna.char_status` answers against the
status `idna`'s own copy of the table gives, with the STD3 statuses
derived from the ASCII rule as UTS #46 before version 15.1 wrote them.

Run from the package root, with the `idna` package installed:
    python3 tools/differential.py
"""
import codecs
import json
import random
import subprocess

import bisect

import idna
from idna import uts46data

SEED = 20260927
OUT = 'tests/differential_tests.nv'

POOLS = [range(0x20, 0x7F), range(0xC0, 0x250), range(0x391, 0x3CA), range(0x410, 0x450),
         range(0x627, 0x64B), range(0x905, 0x940), range(0x4E00, 0x4F00), range(0xAC00, 0xAD00),
         range(0x1F300, 0x1F320), range(0x10400, 0x10450)]
WORDS = ['bücher', 'münchen', 'straße', 'café', 'ελλάδα', 'παράδειγμα', 'пример', 'москва',
         'испытание', '例子', '中文', '日本語', 'テスト', '한국어', 'مثال', 'בדיקה', 'उदाहरण',
         'example', 'test', 'novo', 'lang', 'faß', 'ǅemal', 'ﬁle', 'Ⅻ', 'ÅNGSTRÖM', 'ςίσυφος']
TLDS = ['com', 'org', 'de', 'рф', '中国', 'example']


def text(s):
    return json.dumps(s, ensure_ascii=False).replace('$', '\\$')


def main():
    rng = random.Random(SEED)
    puny = []
    while len(puny) < 300:
        pool = rng.choice(POOLS)
        other = rng.choice(POOLS)
        s = ''.join(chr(rng.choice(pool if rng.random() < 0.7 else other))
                    for _ in range(rng.randint(1, 20)))
        if '"' in s or '\\\\' in s:
            continue
        encoded = s.encode('punycode').decode('ascii')
        puny.append((s, encoded))
    domains, tried = [], 0
    while len(domains) < 200 and tried < 20000:
        tried += 1
        labels = [rng.choice(WORDS) for _ in range(rng.randint(1, 3))]
        name = '.'.join(labels + [rng.choice(TLDS)])
        if rng.random() < 0.3:
            name = name.upper()
        try:
            ascii_form = idna.encode(name, uts46=True, std3_rules=True).decode('ascii')
            unicode_form = idna.decode(ascii_form)
        except idna.IDNAError:
            continue
        if (name, ascii_form) not in [(d[0], d[1]) for d in domains]:
            domains.append((name, ascii_form, unicode_form))
    names = {'V': 'valid', 'M': 'mapped', 'D': 'deviation', 'I': 'ignored', 'X': 'disallowed'}
    statuses = []
    for _ in range(2000):
        plane = rng.choice([0, 0, 0, 0, 1, 2, 3, 14, 15, 16])
        cp = plane * 0x10000 + rng.randrange(0x10000)
        at = bisect.bisect_right(uts46data.uts46_starts, cp) - 1
        letter = chr(uts46data.uts46_statuses[at])
        name = names[letter]
        repl = uts46data.uts46_replacements[at] or ''
        ldh = lambda c: c.isascii() and (c.isalnum() or c in '-.')
        if letter == 'V' and cp < 0x80 and not ldh(chr(cp)):
            name = 'disallowed_STD3_valid'
        if letter == 'M' and any(ord(c) < 0x80 and not ldh(c) for c in repl):
            name = 'disallowed_STD3_mapped'
        statuses.append((cp, name))
    out = ['// differential_tests.nv — punycode against the Python codec, and UTS #46',
           '// against the idna package.',
           '//',
           '// Written by tools/differential.py; do not edit by hand.  %d strings' % len(puny),
           '// with their punycode, and %d domains with their ASCII and Unicode' % len(domains),
           '// forms.',
           '',
           'use std.test',
           'use punycode',
           'use punyidna',
           'use udata',
           '',
           'fn strings() -> [(Str, Str)]',
           '    [']
    for i, (s, e) in enumerate(puny):
        out.append('        (%s, %s)%s' % (text(s), text(e), ',' if i < len(puny) - 1 else ''))
    out += ['    ]', '', 'fn domains() -> [(Str, Str, Str)]', '    [']
    for i, (n, a, u) in enumerate(domains):
        out.append('        (%s, %s, %s)%s' % (text(n), text(a), text(u), ',' if i < len(domains) - 1 else ''))
    out += ['    ]', '', 'fn statuses() -> [(Int, Str)]', '    [']
    for i, (cp, name) in enumerate(statuses):
        out.append('        (0x%X, "%s")%s' % (cp, name, ',' if i < len(statuses) - 1 else ''))
    out += ['    ]',
            '',
            '@test',
            'fn test_the_mapping_table_agrees_with_the_idna_package() [io]',
            '    let d = udata.data_full()',
            '    for row in statuses()',
            '        let (cp, name) = row',
            '        test.case("U+${cp}")',
            '        test.assert_eq(punyidna.status_name(punyidna.char_status(d, cp)), name)',
            '',
            '@test',
            'fn test_punycode_agrees_with_pythons_codec() [io]',
            '    for row in strings()',
            '        let (s, expected) = row',
            '        test.case(expected)',
            '        match punycode.encode(s)',
            '            Ok(p)  => test.assert_eq(p, expected)',
            '            Err(e) => test.fail(e.message())',
            '        match punycode.decode(expected)',
            '            Ok(u)  => test.assert_eq(u, s)',
            '            Err(e) => test.fail(e.message())',
            '',
            '@test',
            'fn test_uts46_agrees_with_the_idna_package() [io]',
            '    let d = udata.data_full()',
            '    for row in domains()',
            '        let (name, ascii, shown) = row',
            '        test.case(name)',
            '        match punyidna.to_ascii(d, name, punyidna.strict())',
            '            Ok(a)  => test.assert_eq(a, ascii)',
            '            Err(e) => test.fail(e.message())',
            '        match punyidna.to_unicode(d, ascii, punyidna.strict())',
            '            Ok(u)  => test.assert_eq(u, shown)',
            '            Err(e) => test.fail(e.message())',
            '']
    open(OUT, 'w').write('\n'.join(out))
    subprocess.run(['novo', 'fmt', OUT], check=True, stdout=subprocess.DEVNULL)
    print('%d strings, %d domains, %d statuses' % (len(puny), len(domains), len(statuses)))


if __name__ == '__main__':
    main()
