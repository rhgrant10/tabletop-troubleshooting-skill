# tabletop-troubleshooting

A [Claude Code](https://code.claude.com/docs/en/overview) skill for troubleshooting tabletop drills. You investigate an incident by saying what you want to find out and which commands you’d run; Claude plays the entire environment: command output, logs, metrics, tickets, and messages from coworkers on other teams. You keep going until you find the root cause, then Claude debriefs you and logs what you practiced.

Ask a language model to make up incidents and you mostly get the same few back: a service with high p99 latency after a deploy, caused by a connection-pool bug. `tabletop-troubleshooting` doesn't let the model choose. Each scenario is rolled by real randomness from a structured option space of 18 axes and about 190 values, filtered by coherence rules, and weighted toward what your history hasn't covered yet.

## Quick start

1. **Fork this repo**, or copy `.claude/skills/tabletop-troubleshooting/` into a repo you already use with Claude Code.
2. Open the repo in Claude Code: the terminal, the desktop app, [claude.ai/code](https://claude.ai/code), or the **Code** tab in the Claude mobile app.
3. Run:

   ```
   /tabletop-troubleshooting
   ```

That starts a coached drill on Linux and distributed systems at medium difficulty. To change it, describe what you want in plain words:

```
/tabletop-troubleshooting interview, storage, hard
/tabletop-troubleshooting junior, databases, no security stuff
/tabletop-troubleshooting learn, GPU clusters, pin device fleet
```

Type `options` at any point to see the modes, domains and axes you can choose from.

Working from a fork is the smoothest setup. The skill commits each scenario to your log, so your coverage history follows you between your laptop and phone.

## Modes

| Mode | Claude's role | Scenario weighting | Time box |
| --- | --- | --- | --- |
| `drill` (default) | Coach: supplies commands when you know the goal but not the syntax | Favors what your log rarely covers | None |
| `learn` | Tutor: hints where to look next and explains each output | Favors what your log rarely covers | None |
| `junior` | Junior engineer at the keyboard: you lead, it runs commands and occasionally misreads them | Favors what your log rarely covers | None |
| `interview` | Interviewer: nudges with questions only, never directions | Even across commonly interviewed scenarios | 50 minutes |

`junior` practices running an incident through someone else. Claude plans a few realistic mistakes in its summaries, such as calling high load average CPU saturation when it's really I/O wait. Its raw output is always truthful, so a careful lead can catch every mistake from the evidence.

## Config

Every setting is optional. Plain words work, and so do the codes from `option_space.md`.

| Setting | Values | Default |
| --- | --- | --- |
| Mode | `interview`, `drill`, `learn`, `junior` | `drill` |
| Domain | one or more of 17 domains, e.g. Linux internals, networking, storage, databases, GPU/HPC, security, sociotechnical; can be weighted (`D2:3,D4:1`) | Linux + distributed systems |
| Difficulty | `easy`, `medium`, `hard`: changes only how the scenario is written (signal strength, red herrings, noise), never what gets rolled | `medium` |
| Overrides | pins ("pin device fleet"), exclusions ("no security stuff"), a coordinate string, or a named scenario of your own | none |

Before rolling, Claude echoes how it resolved your words, e.g. `Resolved: drill · D4:2, D5:1 · medium · pin E7 · exclude D11`, so misreadings get caught early.

## How a session runs

1. **Roll.** `roller.py` picks a value on every axis and prints it **sealed**, as base64. Claude decodes it privately, then checks that decode with `roller.py verify`, which prints only `match` or `mismatch`.
2. **Investigate.** You get a briefing with only what you'd know at the start, then you query the environment turn by turn. `pause` and `resume` freeze and restart the scenario clock.
3. **Reveal.** When you declare a root cause (or give up), Claude asks for a 60-second mitigation and a prevention plan. Then it unseals the roll with `roller.py decode`, so the reveal comes from code rather than memory.
4. **Debrief.** Claude grades how you scoped the blast radius, whether you reasoned with USE (utilization, saturation, errors) or RED (rate, errors, duration), whether you predicted outputs before seeing them, whether you spotted contradictions, and whether you mitigated before root-causing. Command accuracy matters least.
5. **Log.** Claude adds a row to `scenario_log.md` and commits it. Future rolls steer away from what you've already done.

## The option space

`option_space.md` defines each scenario as one value per axis, grouped in tiers:

| Tier | Axes |
| --- | --- |
| 0 | **D** domain (set in your config, not rolled) |
| Rolled first | **A** assignment: live incident, forensics, pre-mortem, recurrence, customer escalation… |
| 1: system context | **R** role · **W** workload · **S** state model · **G** dependency position · **E** environment · **F** fault location |
| 2: the fault | **L** root-cause layer · **M** mechanism · **T** timing · **N** trigger · **C** cause structure · **I** impact |
| 3: presentation | **Y** first symptom · **B** blast radius · **O** evidence quality · **X** mitigation constraints |

A rolled scenario looks like this, though you'll only see it after the reveal:

```
D2 · R2 W1 S1 G3 E3 F3 · L12 M9 T5 N7 C3 I1 · Y14 B8 O4 A1 X6
```

That one is an auth service whose token-signing certificate expired during a change freeze. The symptom is permission errors in everything except auth itself, and a recent deploy is a red herring.

### Rules

The rules table in `option_space.md` keeps rolls coherent. It's machine-read, with a small syntax:

| Type | Effect | Example |
| --- | --- | --- |
| Hard | Filters out impossible combinations | `G in {G3}` → `B in {B8}`: a foundational dependency failing means everything except the broken thing looks broken |
| Prefer / Avoid | Multiplies a value's weight by 3 or 0.25; improbable stays possible | `M in {M9}` → `{N7,T5}`: expiry bugs usually come from time passing |
| Writer | An obligation on the scenario text, not the roll | `E in {E4,E5}`: no host shell on a managed service |

When Claude runs into a combination that's impossible but that no rule caught, it proposes a new Hard rule in the debrief. The rules grow from real gaps.

## Customizing

Everything lives in `.claude/skills/tabletop-troubleshooting/`:

- `option_space.md`: add values, rules, or edit the interview subset. Keep the table formats; the roller parses them.
- `scenario_log.md`: your history. Edit or prune rows freely.
- `SKILL.md`: the instructions Claude follows.

After editing the option space, validate it:

```
python3 .claude/skills/tabletop-troubleshooting/roller.py check \
  --space .claude/skills/tabletop-troubleshooting/option_space.md \
  --log .claude/skills/tabletop-troubleshooting/scenario_log.md
```

`check` parses everything, reports unknown codes and rules that constrain an axis rolled before their condition, then stress-tests thousands of rolls in every mode.

## Roller reference

`roller.py` needs only Python 3 and its standard library.

| Command | Purpose |
| --- | --- |
| `roll --space S --log L [--mode M] [--domain D] [--pin P] [--exclude X] [--window N]` | Roll a sealed scenario. `--window` sets how many recent log rows count for coverage (default 20). |
| `verify TOKEN "COORDS"` | Check a decode against a token; prints only `match` or `mismatch` |
| `decode --space S TOKEN` | Unseal a token: coordinates, value names, Writer notes, and a ready-to-paste log row |
| `options --space S` | Print the config menu |
| `check --space S [--log L]` | Validate the option space and stress-test the rules |

The roller rolls axes in a fixed order, applies Hard rules as filters and soft rules as weights, and backtracks when the Hard rules leave no candidates. In coverage modes, it weights each value by `1 / (1 + recent uses)` and never reuses a root-cause layer + mechanism pair from your log.

## Caveats

- **Spoilers are kept out of sight, not made impossible.** Claude Code shows tool output and, depending on your settings, Claude's reasoning. If you expand them mid-scenario you may see more than you meant to.
- **The interview subset is a judgment call** about what typical SRE and Linux troubleshooting interviews ask, not measured data. Adjust it to what your interviews actually look like.
