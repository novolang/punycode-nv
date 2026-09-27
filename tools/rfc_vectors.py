#!/usr/bin/env python3
"""Write tests/rfc3492_tests.nv from RFC 3492 section 7.1.

The sample strings (A) to (S) are read out of the RFC's own text: the
code points as the `u+XXXX` lines list them, and the punycode as the
`Punycode:` line gives it, with the backslash line continuations
joined.  Nothing is typed by hand.

The RFC's encoder writes the mixed-case annotation of its appendix A,
an upper-case digit for a code point it lists as `U+`.  This package's
encoder writes digits in lower case, as IDNA requires, so the suite
encodes to the RFC's string with its digits lowered, and decodes the
RFC's string exactly as printed.

Run from the package root:
    python3 tools/rfc_vectors.py [rfc3492.txt]
With no argument the text is fetched from rfc-editor.org.
"""
import re
import subprocess
import sys
import urllib.request

URL = 'https://www.rfc-editor.org/rfc/rfc3492.txt'
OUT = 'tests/rfc3492_tests.nv'


def main():
    if len(sys.argv) > 1:
        text = open(sys.argv[1]).read()
    else:
        text = urllib.request.urlopen(URL).read().decode('ascii')
    section = text[text.index('\n7.1 Sample strings'):text.index('\n7.2 ')]
    # Drop the page breaks, which interrupt a sample.
    section = re.sub(r'\n\n\n+Costello[^\n]*\n\x0c?\n?RFC 3492[^\n]*\n', '\n', section)
    samples = re.findall(r'\n   \(([A-S])\) ([^\n]*)\n((?:(?:       [^\n]*)\n)+)', section)
    rows = []
    for letter, title, body in samples:
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        cps, puny = [], None
        joined = ' '.join(lines)
        m = re.search(r'Punycode: (.*)$', joined)
        puny = m.group(1).replace('\\ ', '')
        for cp in re.findall(r'[uU]\+([0-9A-F]{4})', joined[:m.start()]):
            cps.append(int(cp, 16))
        cut = puny.rfind('-')
        plain = puny[:cut + 1] + puny[cut + 1:].lower()
        rows.append((letter, title.strip(), cps, puny, plain))
    assert [r[0] for r in rows] == list('ABCDEFGHIJKLMNOPQRS'), [r[0] for r in rows]
    out = ['// rfc3492_tests.nv — the sample strings of RFC 3492 section 7.1.',
           '//',
           '// Written by tools/rfc_vectors.py from the RFC\'s own text; do not edit',
           '// by hand.  Each row is a sample\'s code points, its punycode as the RFC',
           '// prints it, and the same with the digits in lower case, which is',
           '// what an encoder without the RFC\'s mixed-case annotation writes.',
           '',
           'use std.test',
           'use punycode',
           '',
           'fn samples() -> [(Str, [Int], Str, Str)]',
           '    [']
    for i, (letter, title, cps, puny, plain) in enumerate(rows):
        comma = ',' if i < len(rows) - 1 else ''
        name = '(%s) %s' % (letter, title.replace('"', "'").replace('$', '\\$'))
        out.append('        ("%s", [%s], "%s", "%s")%s' % (name, ', '.join('0x%04X' % c for c in cps),
                                                           puny.replace('$', '\\$'),
                                                           plain.replace('$', '\\$'), comma))
    out += ['    ]',
            '',
            '@test',
            'fn test_every_sample_encodes_to_the_rfcs_punycode_and_back() [io]',
            '    for s in samples()',
            '        let (name, cps, printed, lowered) = s',
            '        test.case(name)',
            '        match punycode.encode(punycode.text_of(cps))',
            '            Ok(p)  => test.assert_eq(p, lowered)',
            '            Err(e) => test.fail(e.message())',
            '        match punycode.decode(printed)',
            '            Ok(u)  => test.assert(punycode.code_points(u) == cps)',
            '            Err(e) => test.fail(e.message())',
            '']
    open(OUT, 'w').write('\n'.join(out))
    subprocess.run(['novo', 'fmt', OUT], check=True, stdout=subprocess.DEVNULL)
    print('%d samples' % len(rows))


if __name__ == '__main__':
    main()
