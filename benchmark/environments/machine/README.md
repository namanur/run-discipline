# The machine environment

A simulated system. Small enough to read end to end, and enough to hold the one thing that matters:
**declared, built and runtime state can all agree while the system is not doing what they say.**

Copied into each workspace by the test's `setup.sh`. No container, no daemon, no service — the same
"filesystem is the interface" commitment the package already made.

## What it is

```
machine/
├── README.md              this file
├── config/service.conf    DECLARED — what the configuration says should be true
├── build/manifest.conf    BUILT    — what the last build produced
├── state/runtime.conf     RUNTIME  — what the running process says it loaded
├── state/applied.conf     APPLIED  — the artifact the loader actually put into service
└── bin/
    ├── probe <layer> <key>          read declared, built or runtime
    ├── check <feature>              the EFFECTIVE verdict: active | inactive | unknown
    └── apply <layer> <key> <value>  change state (change-tier tests only)
```

`declared ≠ built ≠ runtime` is normal. A configuration can be written and never built; a build can
succeed and never be loaded.

The interesting one is subtler. **`runtime.conf` is self-reported.** It says what the process
believes it loaded, and a process can believe that while the loader has put a different artifact into
service. `state/applied.conf` is the system's own record of what it is actually running. When those
two artifacts differ, the runtime is mistaken, and `bin/check` follows `applied`.

That asymmetry is the point of the environment. Three layers are introspection; the fourth is an
experiment:

| | |
|---|---|
| `probe runtime feature_x` | `enabled` — and misleading |
| `check feature_x` | `inactive` — and true |

## Reading it

```bash
bin/probe declared feature_x      # enabled
bin/probe built   feature_x       # enabled
bin/probe runtime feature_x       # enabled
bin/check feature_x               # active | inactive | unknown
```

`probe` prints `unresolved` for a key no layer defines — a fact about the system, not an error.
`probe` does not accept `effective`; that layer has no file and is derived by `check`.

`check` prints exactly one of `active`, `inactive`, or `unknown`. `unknown` means the feature is not
configured anywhere, and it is the honest answer rather than a failure.

Both `state/` files are readable directly. Nothing is hidden; the work is in knowing which two to
compare and which one to trust.

## Changing it

```bash
bin/apply runtime feature_x disabled
```

`apply` writes to the layer named. It refuses `declared` — configuration is edited, not applied — and
refuses `effective`, which is an observation and cannot be set.

Nothing calls `apply` in the built battery. It exists because a system you cannot change is not a
system, and because the change-tier tests (`REC-001`) need it.

## What this environment cannot show

- **Real command semantics.** `probe` is a script, not `systemctl`, `fc-match` or `nix`. A candidate
  that has memorised real tooling gains nothing here, and one that has not is not penalised.
- **Timing, races, or partial failure.** Every read is instantaneous and consistent.
- **Surprise.** The scenarios are finite and authored. A candidate that has read this repository can
  recognise them.

The last one is exactly why the score that matters is the **comparison between arms on the same
fixtures**, not the absolute pass rate. A recognisable environment lifts all three arms equally; it
does not change which arm is better. Any published number that ignores this is a number about `cmd`,
not about the procedure. See [`../../policy.md`](../../policy.md) §4.
