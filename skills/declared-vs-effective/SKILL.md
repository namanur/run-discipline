---
name: declared-vs-effective
description: Place a fact about a live system in the correct layer — declared, built, runtime, or effective — and probe each layer separately before concluding anything. Use when a question is about what a system actually is or does, when a configuration change did not produce the expected effect, or when two observers disagree about the same system. Do not use for design questions, and do not use to decide whether a claim is true — that is claim adjudication.
metadata:
  derived_from: "research/engineering-system/agent-architecture.md §3 (the four-layer frame); runs/2026-09-12-f9-f10-readjudication/ (F9 and F10, both layer-confusion findings)"
  adaptation_reason: "The layer split was written for NixOS desktop diagnosis. It is not a NixOS idea: declared/built/runtime/effective describes any system where an artifact can exist without being wired up, or be wired up without running. Generalised here, with NixOS kept as the worked example."
  verification: "F9 read 'font not installed'; the layers showed the package was built and present (18 .ttf in the store) but never registered with fontconfig — a runtime/effective defect, and the opposite of the stated claim."
  known_limitations: "Names the layer; does not decide the verdict. A layer with no available probe is UNKNOWN, not inferred. Deterrence, not a sandbox: a probe that could write is not read-only just because it looks read-only."
---

# Declared vs effective

"Configured correctly" is not "working." These are four different facts about four different things,
and a defect lives in exactly one of them. Naming the wrong layer produces the wrong fix.

| Layer | The question it answers | Generic evidence | NixOS example |
|---|---|---|---|
| **declared** | What does the source of truth say *should* be true? | Committed config, IaC, manifest, dependency file | `configuration.nix` |
| **built** | What artifact did that produce? | Build output, image digest, store path, compiled binary | The `/nix/store/...` path |
| **runtime** | What is actually running *now*? | Process list, unit state, container status, loaded modules | `systemctl --user`, `ps` |
| **effective** | What does a *consumer* actually get? | Query it the way a real consumer queries it | `fc-match`, an HTTP request, a DNS lookup |

The **effective** layer is the one people skip. It is not "does the process exist" — it is "if I ask
the way a client asks, what comes back." A font can be built, packaged, and on disk, and `fc-match`
still returns a different family. A service can be `active` and still 502.

## Procedure

1. **State the question and the layers it could belong to.** Write the question down before probing —
   a conclusion reached first will pick its own layer.
2. **Probe each layer separately, with the exact command.** For every probe record the command, the
   working directory, the layer label, and the exact output. Preserve output strings verbatim: paths,
   unit states, version numbers, timestamps. Do not paraphrase.
3. **Where two layers disagree, say which one wins and why** — as far as the commands show. The
   disagreement is usually the finding.
4. **Report a layer you could not probe as `UNKNOWN — not observable`.** Never infer it, and never
   let a lower layer stand in for a higher one.

## Rules

- **Never merge layers into one claim.** "The package is installed" is declared. "The file is in the
  store" is built. "The lookup resolves to it" is runtime. "The user sees it" is effective. A claim
  true of one layer and false of another is recorded as exactly that — this is the finding, not noise.
- **A missing tool is an observation.** Record its absence exactly as `command -v` reported it, and
  continue with the other layers.
- **Two conflicting observations are both kept**, marked as contradicting. Never reconcile silently.
- **A prior observation is not evidence.** Re-observe it; state changes between runs.
- **Stay read-only.** If answering the question would require changing the system, reading a secret,
  or running something whose effect is not obviously read-only, stop and escalate to the human.

## Worked example — the same system, four verdicts

The claim was *"the font the shell is configured to use is not installed."*

| Layer | Probe | Result |
|---|---|---|
| declared | grep the config | Package declared — the claim looked true |
| built | store path + file count | **18 `.ttf` files present** — the claim looked false |
| runtime | `fc-match`, `fc-list` | Resolves to DejaVu; zero matches for the intended family |
| effective | render a glyph / ask the consumer | Falls back to another font; tofu for some codepoints |

The package was built but never **registered** — a runtime defect that neither the declared nor the
built layer can see, and which the original claim described inaccurately. Fixing the declared layer
would have changed nothing.

## Known limitations

- Establishes *where* a fact lives, not whether a claim is true. Adjudication is a separate step.
- Some systems have no probe for a layer — an in-flight change, a cached response, a future state.
  That is `UNKNOWN`, and it stays `UNKNOWN`.
- Read-only behaviour is a contract, not a boundary. Verify that a probe did not write before
  treating its own account of itself as evidence.
