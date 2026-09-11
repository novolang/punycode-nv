# punycode-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`.  Installing this package works;
calling it panics with `not implemented`.

## What this is

The four characters in front of an international domain name, and
everything behind them.

`bücher.example` cannot travel through DNS, which speaks a
thirty-seven-character alphabet from 1987.  So it is rewritten as
`xn--bcher-kva.example` — the basic characters kept, the rest described
by a run of base-36 digits — and rewritten back for a person to read.
RFC 3492 is the rewriting; UTS #46 is everything around it, which is
where the difficulty actually lives.

Four surfaces, and a reader should know which one they are on.

| surface | module | reach for it when |
| --- | --- | --- |
| the **arithmetic** | `punyboot` | you are on a device |
| the **codec** | `punycode` | you have one label and want the other form |
| the **processing** | `punyidna` | you have a domain name |
| the **refusals** | `punyerr` | you are reporting why a name failed |

## Adding it, and checking it

```bash
novo pkg add punycode-nv       # into your novo.toml
novo pkg build                 # type- and effect-check the package
novo test --isolate tests/punycode_tests.nv
```

`novo test` is red today and that is the point of the release: all
forty-nine assertions fail with `not implemented: <module>.<fn>`.  They
turn green one at a time as bodies land.

## The one example that will work

```novo
use punyidna
use udata

fn main() [io]
    let d = udata.data_full()
    match punyidna.to_ascii(d, "bücher.example", punyidna.nontransitional())
        Ok(s)  => println(s)   // xn--bcher-kva.example
        Err(e) => println(e.message())
```

## The load-bearing interface

`punyboot.adapt(delta, numpoints, firsttime, params) -> Int`.

Punycode is a generalised variable-length integer whose DIGIT
THRESHOLDS MOVE as the encoding proceeds, and `adapt` is what moves
them.  After each delta the bias is recomputed from how large that
delta was, so a string whose characters are close together spends fewer
digits per character than one whose characters are scattered — and a
Chinese label and a Greek label both come out short without either
paying for the other's range.

Everything else in `punyboot` exists to serve it: `threshold` turns the
bias into the number system's shape, `emit_delta` and `digit_push` walk
that shape in each direction, and `PunyState` is the five integers the
walk needs.  The `firsttime` flag is not a convenience — the damping on
the first delta is what stops one early outlier from making every
following character expensive.

## The device claim is built

`tests/embedded_probe.nv` compiles `punyboot` to a Cortex-M4 ELF for
`--target=nrf52-qemu`, and the consumer that makes it worth having is a
device with a display.

**Showing a domain name to a person is the one security decision
firmware cannot delegate to its host**, because a name rendered on the
host is a name the host could have replaced.  A payment terminal
showing where a transaction is going, or a device confirming what it is
pairing with, has to decode `xn--` itself — and it has a few kilobytes
of RAM to do it in.  `punyboot` is five integers of state and no
buffer, so it does.

`punycode`, `punyidna` and `punyerr` are deliberately outside the
probe: they speak `Str` and `Cursor`, the embedded runtime defines
neither, and one host-only function anywhere in a compilation unit is
an undefined symbol at embedded link time whether or not the firmware
calls it.  `punyidna` also needs unicode-nv's tables, which are
hundreds of kilobytes and are not going on a device at all — so the
device half decodes and displays, and the validity rules stay on the
host that can afford them.

## Which call url-nv would make

`orbit/url-nv`'s host parser refuses a non-ASCII host today.  Its
`uri.nv` says so in its own header — *"No IDNA and no punycode: a host
with a byte above 127 is refused with `IdnaUnsupported` rather than
guessed at"* — and `host_problem` is where it happens: the scan over
the host span answers `E_IDNA` for the first byte at or above 128.

The call that replaces that refusal is

```novo norun:pseudo
punyidna.host_to_ascii(d, host) -> Result<Str, PunyError>
```

and the sequence around it is the WHATWG URL standard's own host
parser: run `host_to_ascii` over the host span, then re-run url-nv's
existing forbidden-byte check on the ASCII result, because IDNA can
produce a character the URL grammar still refuses.  `E_IDNA` stops
being a refusal and becomes a conversion, and `UrlError.IdnaUnsupported`
is replaced by whichever `PunyError` the conversion answered.

Two details that decide whether the two packages fit:

**The options are not `strict()`.**  `punyidna.url_options()` is
nontransitional with `use_std3_ascii_rules` OFF and `check_hyphens`
OFF, which is the combination the WHATWG standard names — a URL host is
not a registry application, and refusing `_` would break a great deal
of deployed naming.  It is published as a value rather than left for
url-nv to assemble, so that the decision is visible in one place.

**`to_ascii_into` exists for url-nv specifically.**  That package's
whole design is spans into a string the caller already holds and
allocates nothing in the parse; a `Str` back would be an allocation for
something the caller can already see.  The buffer form is what a
span-based parser wants, and `ascii_len` is how it sizes one first.

## Five things a wrong implementation gets wrong quietly

Each is a test in `tests/punycode_tests.nv`.

**The delimiter is the LAST hyphen.**  A label may hold hyphens of its
own, so a decoder that scanned from the left cuts `pre-fix-kva` in the
wrong place.  Scanning from the right is unambiguous because the digit
alphabet has no hyphen in it.

**A label with no hyphen is entirely digits.**  `bcher-kva` has a basic
part; `4can8pwxg` has none.  The prose describes the delimiter as if it
were always there, and a decoder written from the prose gets this one
wrong.

**An all-ASCII string ends in a bare delimiter.**  RFC 3492 § 7.1's
case (S): `-> $1.00 <-` encodes to `-> $1.00 <--`, with nothing after
the hyphen.

**`ß` resolves to two different places.**  UTS #46 calls it a
DEVIATION: IDNA2003 mapped it to `ss`, IDNA2008 kept it, so `faß.de` is
`xn--fa-hia.de` under the processing every browser has used since 2016
and `fass.de` under the one from 2003.  `nontransitional()` is what a
caller should reach for; `transitional()` exists because a program that
has to agree with something old needs to be able to say so.

**`ToUnicode` never fails on a label.**  A label that decodes to
something invalid is left as it was rather than refused, because
refusing to display a name is worse than displaying it in its encoded
form.  The `Result` in the signature is for the length and structural
refusals that happen before any label is looked at.

## What this is not

**It is not a security check.**  UTS #46 says whether a name is
well-formed under IDNA.  Whether `раypal.com` and `paypal.com` look
alike to a person is UTS #39's confusable detection — a different
specification with a different table — and a caller that assumed this
package did it would be wrong in the one case that matters.  A registry
or a browser that wants that check needs a package that does not exist
on the grid yet.

**It does not fetch the Unicode data.**  Every function that needs a
table takes unicode-nv's `UniData`, the same way that package's own
normalisation does: the 245 KB of normalisation data is a cost a caller
decides to pay, and a package that compiled it in would decide for
them.  A caller that passes the COMPACT data gets `PunyDataIncomplete`
rather than a silently unnormalised name.

**It does not know about registry policy.**  Whether a particular
script may be mixed with another in a particular top-level domain is
that registry's rule, and there are a thousand of them.

## The layer, and why

`core`.  Everything here is arithmetic over characters the caller
already holds, and no function declares an effect: nothing is read,
nothing is written, and the Unicode tables arrive as an argument.

unicode-nv supplies exactly three things — NFC normalisation
(`unorm.normalize`), the general category of a code point
(`uclass.category`), and the `UniData` the two of them read.  UTS #46
is defined in Unicode terms throughout: its mapping table is derived
from the character database and its validity criteria are stated as
category and property tests, so a package that carried its own table
would be carrying a second copy of unicode-nv's data that ages
separately.  `punyboot` uses none of it, which is what keeps the device
claim.

## The reference implementation

RFC 3492 for the encoding and UTS #46 for the processing, with the
`idna` crate (Rust, MIT / Apache-2.0) and Python's `idna` package (BSD)
as the implementations to check against.  Every vector in
`tests/punycode_tests.nv` is from one of those documents — the six
parameters from § 5, `adapt` from § 6.1, the threshold clamp from
§ 6.2, the sample strings from § 7.1, and UTS #46's own `faß.de`
deviation example — so a reader can check the port against the
specification rather than against this package.

## Status

| function | implemented |
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
| `punyerr.error_label`, `.error_offset`, `.error_step`, the `message` impl | no |
