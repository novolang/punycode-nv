# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.0.1 — 2026-09-11

The **interface**, before anyone implements it.  Every signature, every
type and every effect row is published; every body is `todo()`, and the
release is stamped `NOT IMPLEMENTED — interface only`.  Adding this
package works and calling it panics.

- Four modules.  `punyboot` is bootstring's six parameters and its
  delta arithmetic as integers; `punycode` is RFC 3492 over strings and
  into a caller's buffer; `punyidna` is UTS #46's five steps, each
  named and each callable on its own; `punyerr` is one refusal type
  whose variants are grouped by which step said no.
- **`punyboot.adapt` is the load-bearing interface.**  Punycode is a
  variable-length integer whose digit thresholds MOVE as the encoding
  proceeds, and `adapt` is what moves them — which is why a Chinese
  label and a Greek label both come out short without either paying for
  the other's range.
- **The device claim is built.**  `tests/embedded_probe.nv` compiles
  `punyboot` to a Cortex-M4 ELF for `--target=nrf52-qemu`.  Showing a
  domain name to a person is the one security decision firmware cannot
  delegate to its host, because a name rendered on the host is a name
  the host could have replaced; `punyboot` is five integers of state
  and no buffer, so a payment terminal can decode `xn--` itself.
- **Which call url-nv would make is written down**:
  `punyidna.host_to_ascii` replaces its `host_problem`'s `E_IDNA`
  refusal, with url-nv's own forbidden-byte check re-run over the ASCII
  result — the WHATWG URL standard's own sequence.  `url_options()` is
  that standard's combination as a value (nontransitional, STD3 off,
  hyphens unchecked), and `to_ascii_into` exists because url-nv
  allocates nothing in its parse.
- **Five things a wrong implementation gets wrong quietly** are each a
  test: the delimiter is the LAST hyphen; a label with no hyphen is
  entirely digits; an all-ASCII string ends in a bare delimiter (RFC
  3492 § 7.1 case S); `faß.de` resolves to two different places
  depending on which processing is chosen; and `ToUnicode` never fails
  on a label, because refusing to display a name is worse than
  displaying it encoded.
- **Transitional processing is dead and the option remains.**
  `nontransitional()` is what every browser has used since 2016;
  `transitional()` exists because a program that has to agree with
  something old needs to be able to say so.
- **This is not a security check**, and the README says so: UTS #46
  answers well-formedness, and confusable detection is UTS #39 with a
  different table.
- Depends on unicode-nv for exactly three things — NFC normalisation,
  the general category of a code point, and the `UniData` the two read.
  A caller that passes the COMPACT data gets `PunyDataIncomplete`
  rather than a silently unnormalised name.
- Every vector is RFC 3492's or UTS #46's own.
