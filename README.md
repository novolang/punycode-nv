# punycode-nv

A domain name may hold any character a person writes, but the Domain
Name System carries only letters, digits and the hyphen. Punycode is the
encoding that bridges the two: `bücher.example` travels as
`xn--bcher-kva.example`, and is turned back for a person to read. The
encoding is
[RFC 3492](https://www.rfc-editor.org/rfc/rfc3492), and the rules around
it are [UTS #46](https://www.unicode.org/reports/tr46/), Unicode IDNA
Compatibility Processing. This package implements both, over
[unicode-nv](https://novo-lang.org/packages/unicode-nv)'s tables.

**Status: NOT IMPLEMENTED — interface only.** Every function is declared
with its full signature, but every body is a `todo()` that panics when
called. The package is published so its design can be reviewed and
depended on before it is implemented. Version 0.1.0 will be the first
working release.

## What punycode is

A domain name is a sequence of **labels** separated by full stops. Each
label is encoded on its own. A label is **basic** when every character
in it is below code point 128, and a basic label is left alone.

Any other label is rewritten. Its basic characters are copied out first,
then a hyphen, then a run of digits describing the rest. The rewritten
label is marked with the prefix `xn--`, which is called the ACE prefix,
for ASCII Compatible Encoding.

The digits are base 36: the letters `a` to `z`, which are case
insensitive, and then `0` to `9`. They spell a sequence of **deltas**.
Each delta says how far to advance a running code point and a running
position, which together name the next character to insert and where it
goes. RFC 3492 calls the general scheme **bootstring**, and punycode is
bootstring with the six parameters in the table below.

The digit thresholds move as the encoding proceeds. After each delta the
**bias** is recomputed from how large that delta was, so a label whose
characters are close together spends fewer digits per character than one
whose characters are scattered. A Chinese label and a Greek label both
come out short, and neither pays for the other's range. The first
adaptation is damped, so that one early outlier does not make every
following character expensive.

RFC 3492 is only the rewriting. Deciding which characters may appear at
all, mapping upper case to lower, normalising, and checking the rules
that apply to scripts written right to left is UTS #46, and that is
where most of the difficulty is. UTS #46 names two vintages of the
processing. **Nontransitional** processing is what every browser has
used since 2016. **Transitional** processing maps four **deviation**
characters the older IDNA2003 way.

| Quantity | Value |
| --- | --- |
| Digit alphabet size (`base`) | 36 |
| Smallest digit threshold (`tmin`) | 1 |
| Largest digit threshold (`tmax`) | 26 |
| Bias skew (`skew`) | 38 |
| Damping on the first delta (`damp`) | 700 |
| Starting bias (`initial_bias`) | 72 |
| Starting code point (`initial_n`) | 128 |
| Delimiter | `-`, ASCII 45 |
| ACE prefix | `xn--`, 4 characters |
| Longest label | 63 characters |
| Longest domain name | 253 characters |
| Highest code point a delta may name | `0x10FFFF` |

## Install

```
novo pkg add punycode-nv
```

## Example

```novo
use punyidna
use udata

fn main() [io]
    // The Unicode tables. IDNA needs normalisation and character
    // categories, so the full data is required and the compact set is
    // refused.
    let d = udata.data_full()

    // One domain name to the form a resolver takes. The options are the
    // processing every browser uses.
    match punyidna.to_ascii(d, "bücher.example", punyidna.nontransitional())
        // xn--bcher-kva.example
        Ok(s)  => println(s)
        Err(e) => println(e.message())
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a `not implemented: <module>.<fn>`
panic. The tests are the specification the implementation will have to
satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `punyboot` | The six parameters and the delta arithmetic as integers: the digit alphabet, the moving threshold, the adaptation, the limits, and the encode and decode steps. |
| `punycode` | RFC 3492 over one label: encode, decode, the ACE prefix, the delimiter rule, the canonical round trip, and the two size questions. |
| `punyidna` | UTS #46 over a whole domain: the option sets, the mapping table's statuses, the validity rules, the bidi and joiner checks, and the two conversions in both directions. |
| `punyerr` | The eighteen refusals, each naming the label it is about, and the accessors that pull the label, the offset and the step out of one. |

## How to choose an entry point

**`punyidna.to_ascii` and `punyidna.to_unicode` take a whole domain
name.** They map, normalise, split into labels, encode or decode each
one, and apply the validity rules. This is the call for a program that
has a name a person typed.

**`punyidna.host_to_ascii` and `host_to_unicode` are the same for a URL
host.** They use `punyidna.url_options`, which is the combination the
WHATWG URL standard names.

**`punycode.encode` and `punycode.decode` take one label and do no
checking.** Reach for them when you are implementing something other
than a domain name, or when the checking has already happened.

**`punyboot` is the arithmetic for firmware.** It takes and answers
integers, and the caller drives the loop. See "Running on a
microcontroller".

**The `*_into` calls write into a `Cursor` you already own.**
`punyidna.ascii_len` sizes the destination first. A parser that answers
spans into a string it already holds wants these.

## The rules a user needs

1. **The delimiter is the last hyphen in the label.** A label may hold
   hyphens of its own, and the digit alphabet has no hyphen in it. A
   decoder that scanned from the left would cut `pre-fix-kva` in the
   wrong place. RFC 3492 section 6.2 is the decoding procedure.
2. **A label with no hyphen is all digits.** It has no basic characters
   at all. `bcher-kva` has a basic part and `4can8pwxg` does not.
3. **An all-basic string encodes with a bare delimiter on the end.**
   RFC 3492 section 7.1, case (S): `-> $1.00 <-` becomes
   `-> $1.00 <--`.
4. **A delta that passes the overflow bound is refused, not wrapped.**
   RFC 3492 section 6.4 requires the check. A wrapped delta decodes to a
   different string, and a name that decodes two ways is a phishing
   tool. `punyboot.overflow_limit` is the bound and `PunyOverflow` is
   the refusal.
5. **An `xn--` label must be the encoding an encoder would have
   produced.** UTS #46 requires the round trip, because two encodings of
   one name are two names to any comparison. `PunyNotCanonical` and
   `PunyPointlessEncoding` are the two ways a label fails it.
6. **An encoder writes lower case only.** Digit characters are case
   insensitive on the way in, and DNS resolvers compare `xn--` labels as
   bytes.
7. **`ToUnicode` never refuses a label.** A label that decodes to
   something invalid is left in its encoded form, because refusing to
   display a name is worse than displaying it encoded. The `Result` in
   the signature is for the length and structural refusals that happen
   before any label is read.
8. **`ß` resolves to two different places.** UTS #46 calls it a
   deviation. `faß.de` is `xn--fa-hia.de` under nontransitional
   processing and `fass.de` under transitional. Reach for
   `punyidna.nontransitional`. `punyidna.transitional` is for a program
   that must agree with something older.
9. **The Unicode tables are the caller's argument.** Every function that
   needs one takes a `UniData`. The full data is hundreds of kilobytes,
   and a package that compiled it in would decide that cost for the
   caller. The compact set is refused with `PunyDataIncomplete` rather
   than producing a silently unnormalised name.
10. **Split the domain after mapping, not before.** UTS #46 maps three
    other characters to the full stop, among them IDEOGRAPHIC FULL
    STOP. `punyidna.split_labels` splits on `.` alone, which is correct
    only in that order.
11. **The option set is part of the answer.** `nontransitional` is what
    browsers use, `strict` is what a registry checking a name for sale
    would use, and `url_options` turns the STD3 ASCII rules and the
    hyphen checks off, as the WHATWG URL standard requires. The
    underscore in a host name is the case those two options decide.
12. **The bidi rule applies to a whole domain.** RFC 5893 asks whether
    any label holds a right-to-left character, and applies its
    conditions to every label if one does. `punyidna.is_bidi_domain`
    answers the question, and `PunyBidiRule` names the numbered
    condition that failed.
13. **A label may not begin with a combining mark.** UTS #46 forbids it
    whatever the options say.
14. **The 63-character label limit includes the `xn--` prefix.** So does
    the 253-character domain limit. `punyidna.fits_dns` and
    `punyidna.ascii_len` answer before a caller commits, and
    `verify_dns_length` is the option that turns the check off for a
    name being converted only for display.

## Running on a microcontroller

novo-lang lets a package state which of its modules can run on a device
with no heap allocator, and the compiler checks that claim on every
build. Here the claim covers `punyboot` and nothing else. It takes and
answers `Int` and `Bool`, its state is five integers, and it holds no
buffer.

`tests/embedded_probe.nv` is that claim as a program that either builds
or does not. It builds today:

```bash
novo build --target=nrf52-qemu tests/embedded_probe.nv
```

The probe produces a Cortex-M4 executable that reads the parameters,
runs the threshold and the adaptation, and walks a delta in each
direction. It builds and it is not run: every function it calls is a
`todo()` today.

The consumer for this is a device with a display. Showing a domain name
to a person is a decision firmware cannot delegate to its host, because
a name rendered on the host is a name the host could have replaced. A
payment terminal showing where a transaction is going has to decode
`xn--` itself, in a few kilobytes of memory.

**A device cannot use `punycode`, `punyidna` or `punyerr`.** They speak
`Str` and `Cursor`, and the embedded runtime defines neither. One
host-only function anywhere in a compilation unit is an undefined symbol
at link time on a device, whether or not the firmware calls it.
`punyidna` also needs the Unicode tables, which are hundreds of
kilobytes. A device decodes and displays; the validity rules stay on the
host that can afford them.

## What is not included

- **Confusable detection.** Whether `раypal.com` and `paypal.com` look
  alike to a person is UTS #39, a different specification with a
  different table. This package says whether a name is well-formed under
  IDNA, which is a narrower claim than whether it is safe to show.
- **Registry policy.** Whether a particular script may be mixed with
  another under a particular top-level domain is that registry's rule,
  and there are thousands of them.
- **The Unicode tables themselves.** They come from unicode-nv as an
  argument. See rule 9.
- **Name resolution.** This package converts a name. Looking it up is
  [dns-codec-nv](https://novo-lang.org/packages/dns-codec-nv) and the
  standard library's networking.
- **IDNA2008's own protocol document.** The processing here is UTS #46,
  which is what browsers implement.

## Related packages

- [unicode-nv](https://novo-lang.org/packages/unicode-nv) supplies the
  three things this package needs: NFC normalisation, the general
  category of a code point, and the `UniData` both read. It is this
  package's only dependency.
- [url-nv](https://novo-lang.org/packages/url-nv) parses URLs and today
  refuses a host with a byte above 127. `punyidna.host_to_ascii` with
  `punyidna.url_options` is the call that replaces that refusal, and
  `to_ascii_into` is the form its span-based parser wants.
- [dns-codec-nv](https://novo-lang.org/packages/dns-codec-nv) writes the
  wire format a resolver sends, over the ASCII names this package
  produces.
- [base64-nv](https://novo-lang.org/packages/base64-nv) is the other
  text encoding of non-text data on the registry, with a fixed alphabet
  and no adaptation.

## Tests

```bash
novo test tests/punycode_tests.nv      # 49 tests
```

Every vector is from RFC 3492 or UTS #46: the six parameters from
section 5, `adapt` from section 6.1, the threshold clamp from section
6.2, the sample strings from section 7.1, and UTS #46's own `faß.de`
deviation example. The implementations to check a port against are the
`idna` crate in Rust and Python's `idna` package.

The suite asserts that the parameters are the specification's own, that
the first adaptation is damped and every later one halved, that a delta
writes its digits least significant first, that the German sample
encodes to the string everyone cites, that an all-ASCII string ends in a
bare delimiter, that the delimiter is the last hyphen, that the round
trip is what makes a label canonical, that the deviation example
resolves to two different places, that an empty label is not a domain,
that a label may not begin with a combining mark, that the STD3 and
hyphen options are what decide an underscore, that the bidi rule applies
only to a domain that has a right-to-left character, that a compact
`UniData` is refused, and that each refusal names its label and its
step.

The tests compile today and fail at run, each on the `not implemented`
panic that is its body. That is the expected state of an interface
release. They turn green one at a time as bodies land.

## Implementation status

| Item | Implemented |
| --- | --- |
| `punyboot.params`, `.delimiter`, `.is_basic` | no |
| `punyboot.digit_value`, `.digit_char`, `.threshold`, `.adapt` | no |
| `punyboot.overflow_limit`, `.max_label_len`, `.max_domain_len`, `.prefix_len` | no |
| `punyboot.state`, `.skip`, `.advance_to`, `.emit_delta`, `.after_delta` | no |
| `punyboot.digit_scan`, `.digit_push`, `.insertion`, `.after_insertion` | no |
| `punycode.ace_prefix`, `.is_encoded_label`, `.delimiter_at`, `.is_canonical` | no |
| `punycode.encoded_len`, `.encode`, `.encode_into` | no |
| `punycode.decoded_len`, `.decode`, `.decode_into` | no |
| `punycode.encode_label`, `.decode_label` | no |
| `punyidna.nontransitional`, `.transitional`, `.strict`, `.url_options` | no |
| `punyidna.status_name`, `.char_status`, `.map_char`, `.map` | no |
| `punyidna.validate_label`, `.bidi_rule`, `.is_bidi_domain` | no |
| `punyidna.contextj_rule`, `.contexto_rule` | no |
| `punyidna.to_ascii`, `.to_ascii_into`, `.to_unicode`, `.to_unicode_into` | no |
| `punyidna.label_to_ascii`, `.label_to_unicode` | no |
| `punyidna.split_labels`, `.join_labels`, `.ascii_len`, `.fits_dns` | no |
| `punyidna.host_to_ascii`, `.host_to_unicode` | no |
| `punyerr.error_label`, `.error_offset`, `.error_step`, `PunyError.message` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
