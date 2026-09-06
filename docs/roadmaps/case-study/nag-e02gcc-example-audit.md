# NAG `e02gcc` Example Audit

## Status

- **Work unit:** `OPT-DS-ROBUST-BENCH-B`
- **State:** complete
- **Decision:** `D — REJECTED` as a repository fixture source
- **Scope:** source-specific follow-up to `netlib-495-artifact-audit.md`
- **Capabilities evaluated:** `scenario.linear.min_max_loss` and the exact
  sign-dual `scenario.linear.max_min_reward`

This decision rejects copying the NAG example into Optees. It does not reject
Chebyshev approximation as valid mathematical evidence.

## Sources inspected

| Evidence | Location | Audit observation |
| --- | --- | --- |
| Current NAG curve-fitting introduction | <https://support.nag.com/numeric/cl/nagdoc_cl26/pdf/e02/e02intro.pdf> | Identifies `nag_linf_fit (e02gcc)` as the general-linear-function infinity-norm fitting routine. |
| NAG C Library Mark 7 `e02gcc` manual page | <https://www.originlab.com/pdfs/nagcl07/manual/pdf/e02/e02gcc.pdf> | A third-party archival mirror exposes the example, input, and rounded result; the example program is marked Copyright 2001 Numerical Algorithms Group. This is not treated as a canonical redistribution source. |
| NAG Library installation documentation | <https://support.nag.com/doc/inun/cl26/lm6ddl/in.html> | Describes supplied example source, data, and result files as installed NAG Library materials and refers users to the applicable licence agreement. |
| Netlib CALGO Algorithm 495 | <https://netlib.org/toms/495> | Contains the `CHEB` implementation but none of the NAG example data; audited separately. |

The audit did not locate a source-specific permission allowing the NAG example
data or program output to be redistributed under Optees' Apache-2.0 terms.
Public web access is not treated as redistribution permission.

## Correction of the earlier candidate description

The five displayed observations are

| $t_i$ | $y_i$ |
| ---: | ---: |
| 0.0 | 4.501 |
| 0.2 | 4.360 |
| 0.4 | 4.333 |
| 0.6 | 4.418 |
| 0.8 | 4.625 |

They are not fitted by the two-parameter straight line previously described in
the Netlib audit draft. The NAG example fits

\[
y(t)=K e^t + L e^{-t} + M,
\]

which is nonlinear in $t$ but linear in the three decision variables
$x=(K,L,M)$. Its matrix row is

\[
a_i=(e^{t_i},e^{-t_i},1).
\]

The NAG output is printed at limited precision as approximately

- maximum residual: `0.10E-02`;
- solution: `(1.0049, 2.0149, 1.4822)`;
- rank: `3`;
- iterations: `4`.

The former two-variable result `(4.386, 0.155)` with residual `0.115` solves a
different straight-line problem invented during the audit. It must not be
attributed to NAG, Barrodale–Phillips, or Algorithm 495.

## Exact scenario mapping

For residual $r_i(x)=a_i^Tx-y_i$, the min-max payload creates the ordered pair

\[
v_{i,+}(x)=a_i^Tx-y_i,\qquad
v_{i,-}(x)=-a_i^Tx+y_i.
\]

The resulting objective is exactly

\[
\min_x\max_i |r_i(x)|.
\]

Negating every scenario evaluation produces the exact derived max-min problem

\[
\max_x\min_k[-v_k(x)]
=-\min_x\max_k v_k(x).
\]

No public contract or solver semantics need to change.

## Independent temporary experiment

The example was reconstructed only in process memory; no NAG material was added
to the repository or persistent benchmark cache.

SciPy HiGHS produced:

- $K=1.0048603602214945$;
- $L=2.0149335989851136$;
- $M=1.482240077451902$;
- maximum residual $0.0010340366585113636$.

The registered Optees capabilities independently produced:

| Capability | Status | Guarantee | Binding scenarios | Validation |
| --- | --- | ---: | --- | --- |
| `scenario.linear.min_max_loss` | `optimal` | `0.0010340366585124272` | `s0_pos`, `s2_neg`, `s3_pos`, `s4_neg` | `verified` |
| `scenario.linear.max_min_reward` | `optimal` | `-0.0010340366585124272` | `s0_pos`, `s2_neg`, `s3_pos`, `s4_neg` | `verified` |

This establishes compatibility of the mathematical transformation and provides
useful review evidence. It is not a permanent scientific benchmark because the
input and printed reference originate in NAG documentation whose redistribution
permission was not established.

## Decision

The NAG example is rejected as a source for repository fixtures because:

1. the example program explicitly carries NAG copyright;
2. NAG documentation treats example source, data, and results as licensed
   product materials;
3. no Apache-compatible or otherwise suitable redistribution permission was
   identified for the exact example;
4. the public result is rounded and the higher-precision value above is an
   independent recomputation, not a NAG-published oracle at that precision;
5. Optees already has independent analytic scenario fixtures, so copying this
   example is unnecessary for regression coverage.

The numerical coefficients, program, or result must not be committed to
`tests/data/scenario/`. A future permission from NAG could reopen the decision.

## Completion gate

- [x] Exact NAG model distinguished from the earlier invented straight-line model.
- [x] Published rounded output distinguished from independent recomputation.
- [x] Both public Optees capability paths exercised temporarily.
- [x] Redistribution evidence reviewed conservatively.
- [x] No NAG material persisted in the repository or cache.
- [x] Fixture integration rejected and roadmap status updated.

**Gate `ROBUST-BENCH-AUDIT-NAG`: achieved.** No implementation work is
authorized by this audit.

## Next benchmark-specific boundary

If scientific scenario evidence is prioritised further, perform an artifact-
and-source audit of a small set of published two-person zero-sum matrix games
with exact values. Otherwise return to the case-study forecasting evidence gate.
