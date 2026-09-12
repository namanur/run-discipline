# `TASK.md` frontmatter contract

`TASK.md` is the only authored artifact a receipt cannot derive. Everything else in a run is
recoverable from commands, the transcript, or git; the criterion, the verdicts, and the override
exist nowhere else. Author it **before** any probing.

## Fields

| Field | Req | Holds | Authored by |
|---|---|---|---|
| `run` | ✓ | The run directory slug | Human |
| `tier` | ✓ | `read` or `change`. Decides whether an independent review is owed | Human |
| `session_id` | ✓ | The harness session id | Human |
| `session_file` | ✓ | Path to the transcript, **outside** the run directory | Human |
| `request` | ✓ | What was asked, in the requester's terms | Human |
| `criterion` | ✓ | The falsifiable completion condition. See below | Human |
| `agents` | ✓ | Which agents were intended to run | Human |
| `skills` | — | `intended:` authored list; `activated:` the literal `UNKNOWN — not observable` | Human |
| `gates` | — | Authority boundaries for this run | Human |
| `base_state` | ✓ | `git`, `nix_generation`, `captured_at`, `note` — captured, not reconstructed | Human |
| `verdicts` | ✓ | List of `claim` / `verdict` / `by` / `at` / `evidence` / `qualification` | Evidence, ruled by human |
| `override` | ✓ | `null`, or `by` / `why` / `at`. See below | Human |
| `artifacts` | — | `kept` and `lost` — a run that loses an artifact records the reason | Human |
| `result_state` | ✓ | `git`, `nix_generation`, `machine_change` | Human |
| `rollback_tested` | ✓ | Method, tested_at, result — or an explicit `n/a` **with the reason** | Human |

`tier` and `session_file` are additions this contract makes. `tier` is what makes the tier rule
checkable rather than conventional. `session_file` is the single smallest change the executed run's
own retrospective justified: the receipt's session correlation and the blind reader both had to reach
outside the run directory for it.

## The criterion

The highest-value act in the run and the only one no tool can supply. A criterion is falsifiable when
a specific command's output decides it.

| Usable | Not usable |
|---|---|
| "Done when `pytest -q` exits 0." | "The service works." |
| "`fc-match monospace` resolves to the configured family." | "Fonts are fixed." |
| "`git -C /etc/nixos status --porcelain` is empty." | "The repo is clean." |

State it as *condition + command*. If you cannot name the command, you do not yet have a criterion,
and the correct next action is more understanding — not less.

## The override

The override is the artifact of record — the fact that a criterion failed and a human proceeded
anyway. Keep the three parts separate:

```yaml
override:
  by: <who>
  why: <the reason, in their words>
  at: "<ISO-8601>"
```

An override recorded as one prose sentence inside a large transcript is the failure this field
exists to prevent.

## Parser constraints

The reference receipt parser is a hand-rolled YAML subset. Stay inside it:

- **Never use an inline map.** `artifacts: {kept: [], lost: []}` is read as an opaque string. Write
  nested mappings on their own lines. This bug is live in the one existing run.
- Block scalars (`>` folded, `|` literal) and inline lists (`[a, b]`) are supported.
- Quote timestamps and anything containing `:` or `#`.
- Frontmatter must begin at byte 0 and close with `---` on its own line. A parse failure is reported
  as a gap, not silently ignored — but the run then has no criterion, which is worse.
