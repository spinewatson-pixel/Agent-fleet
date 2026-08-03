# Build Verification Framework

Verification is a property of the build, not something a developer remembers to run.

Every registered project produces, on every build: build verification, dependency
validation, end-to-end simulation, contract verification, capability/governance
validation, performance metrics, a regression comparison against the previous
successful build, and a deployment readiness score. If a required gate fails, the
command exits non-zero and prints exactly what failed and why.

```bash
pnpm verify                                 # every registered project
pnpm verify --project nursing-ecosystem     # one project
pnpm verify --only build.types,deps.lockfile
pnpm verify:baseline                        # record a successful run as the new baseline
```

## The eight outputs

| # | Category | Produced by | Blocking |
| --- | --- | --- | --- |
| 1 | `build` | gates declared in the manifest | required gates |
| 2 | `dependencies` | gates declared in the manifest | required gates |
| 3 | `e2e` | gates declared in the manifest | required gates |
| 4 | `contracts` | gates declared in the manifest | required gates |
| 5 | `governance` | gates declared in the manifest | required gates |
| 6 | `performance` | gates declared in the manifest + automatic `duration_ms` | thresholds |
| 7 | regression | derived — current metrics vs. the committed baseline | `severity: "fail"` rules |
| 8 | readiness score | derived — weighted gate outcomes, 0–100 | `policy.minimumScore` |

Categories 1–6 must each be covered by at least one gate. A manifest that omits one
does not score 100 — it fails to verify at all (`missing_category`), which is what
stops coverage from quietly eroding.

## How a gate works

A gate is a shell command. That is the entire integration contract, which is why the
TypeScript control plane and the standard-library Python agent stack use the same
framework with no shared runtime.

```ts
{
  id: "e2e.chains",
  category: "e2e",
  description: "Full simulation of every agent chain",
  command: "python3 ecosystem/verify_gates.py e2e",
  required: true,      // a failure here blocks deployment
  weight: 5,           // contribution to the readiness score
  timeoutMs: 600_000,
  parser: { kind: "json" },
  thresholds: [
    { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
    { metric: "chapter_words", operator: "gte", value: 900, severity: "fail" },
  ],
}
```

### Parsers

| Kind | Contract |
| --- | --- |
| `exitCode` | default; exit status only |
| `json` | the command prints `{"status","metrics":{...},"failures":[...]}` on stdout |
| `regex` | named patterns with one capture group each, applied to stdout + stderr |

For `json`, print the JSON on **stdout** and human detail on **stderr**. The parser
takes the last balanced object, so incidental logging is fine.

### Status rules

A gate is classified in this order, and infrastructure problems outrank whatever the
gate claims about itself:

1. timed out → `fail`
2. non-zero exit → `fail`
3. output could not be parsed → `fail`
4. `severity: "fail"` threshold breach → `fail`; `warn` breach → `warn`
5. a gate may **downgrade** itself via `status`, never upgrade itself
6. a required gate reporting `skip` → `fail`

A threshold naming a metric the gate never produced is a breach, not a pass. This is
the same rule the agent stack applies to its verifier: absence of evidence is not
evidence of health.

## Readiness score

Weighted across gates: `pass` = 1.0, `warn` = 0.6, `fail` = 0, `skip` leaves the
denominator. Normalized to 0–100 and compared against `policy.minimumScore`.

If no weighable gate ran, the score is **0**, never 100.

## Regression comparison

Metrics are flattened to `<gateId>.<metric>` and compared against
`verification/baselines/<project>.json` — committed, so a fresh clone and CI compare
against the same previous successful build a developer does.

```ts
{ metric: "perf.suite.tests_passed", direction: "higher-is-better", tolerance: 0, severity: "fail" }
```

Three cases behave differently on purpose:

- **present on both sides** — compared against the rule's relative tolerance
- **missing from the current run** — a regression in its own right, because a gate
  silently stopped reporting
- **missing from the baseline** — recorded as unmatched, not held against the build,
  so new metrics can appear

Only a build that is not `BLOCKED` may become the next baseline, and `--only` runs
never update it — a partial run is not a description of the build.

## Verdicts

| Verdict | Meaning | Exit |
| --- | --- | --- |
| `READY` | every gate passed, nothing to warn about | 0 |
| `READY_WITH_WARNINGS` | deployable; warnings recorded | 0 |
| `BLOCKED` | at least one blocking condition | 1 |

Blocking conditions: `required_gate_failed`, `missing_category`, `regression_failure`,
`score_below_minimum`, `baseline_missing` (when `policy.requireBaseline`), and
`manifest_invalid`.

A blocked build is a normal outcome, not an exception — the report is always written.
If the harness itself throws, that is also a blocked build, never a pass.

## Onboarding a new ecosystem

1. **Expose six gates.** Anything runnable works. For a non-JavaScript stack the
   simplest route is one entry point per category printing a JSON object:

```python
print(json.dumps({
    "status": "pass",
    "metrics": {"checks_run": 12, "checks_failed": 0},
    "failures": [],
}))
```

Exit non-zero when the gate fails; the framework blocks either way.

2. **Write a manifest** in `src/verification/manifests/<project>.ts` covering all six
   categories, with thresholds and regression rules.

3. **Register it** in `src/verification/manifests/index.ts`.

4. **Record a baseline** with `pnpm verify:baseline` once the project is green.

`tests/verification.manifests.test.ts` then enforces the rest: unique id, full
category coverage, regression rules pointing at real gates, required gates on the
safety-critical categories, and a committed baseline.

## Taking the framework to another repository

The framework imports nothing but Node builtins (`node:fs`, `node:path`,
`node:child_process`). There are no runtime npm dependencies, so sharing it is a file
copy — verified by running it in a clean, unrelated repository with only these files
present:

```
src/verification/*.ts          the framework (12 files, ~1,700 lines)
scripts/verify.ts              the CLI
```

Then in the receiving repo:

1. `package.json` needs `"type": "module"` and a script:
   `"verify": "tsx scripts/verify.ts"`. `tsx` is only needed to execute TypeScript
   directly — compiling with `tsc` or using Node's native TypeScript support works
   equally well. The framework itself needs neither.
2. Write `src/verification/manifests/index.ts` exporting `MANIFESTS` and
   `getManifest`, plus one manifest per project.
3. `pnpm verify:baseline` once green, and commit `verification/baselines/`.
4. Copy `.github/workflows/verify.yml` so it runs without anyone remembering, and
   give any deployment job `needs: verify`.

Nothing else transfers. The manifests are the only repo-specific part, and
`docs/VERIFICATION.md` plus `tests/verification.*.test.ts` are worth copying too —
the tests enforce category coverage on whatever manifests the new repo writes.

## Worked example — the two shipped projects

**`agent-fleet`** wraps commands the project already had (`typecheck`, `lint`,
`build`, frozen-lockfile install, `depcheck`, targeted vitest runs) and adds metrics:
bundle size, tests passed, suite duration.

**`nursing-ecosystem`** is standard-library Python with no `claude` CLI available in
CI. Its gates run the real chains against test doubles
(`ecosystem/simulation/doubles.py`), so the end-to-end gate verifies wiring —
stage order, accumulating carry, prompt placement, database writes, mechanical
scoring — without the model. Its contract gate mechanically checks the stack's own
nine rules; its governance gate checks that nothing schedules itself, that write and
execute tools stay disallowed at the CLI boundary, that every model-calling module
carries a guard, and that every capability unlock is a real evidence count.

That governance gate found a real gap on its first run: `loops.mentor()` called the
model without a guard. The gate was kept and the code was fixed.

## What this does not do

- It does not deploy anything. It decides whether deployment may proceed.
- Gates run sequentially. They share ports, databases and build output, and parallel
  timing metrics would be meaningless.
- The Python end-to-end gate proves wiring, not content quality. Its doubles return
  fixed synthetic text.
- Baselines are per-branch artifacts in git; comparing across long-lived divergent
  branches compares against whatever was last committed to that path.
