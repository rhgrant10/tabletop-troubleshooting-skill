# tabletop-troubleshooting

A [Claude Code](https://code.claude.com/docs/en/overview) skill for troubleshooting tabletop drills. You investigate an incident by saying what you want to find out and which commands you’d run; Claude plays the entire environment: command output, logs, metrics, tickets, and messages from coworkers on other teams. You keep going until you find the root cause, then Claude debriefs you and logs what you practiced.

Ask a language model to make up incidents and you mostly get the same few back: a service with high p99 latency after a deploy, caused by a connection-pool bug. `tabletop-troubleshooting` doesn't let the model choose. Each scenario is rolled by real randomness from a structured option space of 18 axes and about 190 values, filtered by coherence rules, and weighted toward what your history hasn't covered yet.

## Quick start

1. **Install the skill:** copy (or symlink) `skills/tabletop-troubleshooting/` from this repo into `.claude/skills/` in a repo you use with Claude Code, or into `~/.claude/skills/` to have it in every project.
2. Open that repo in Claude Code: the terminal, the desktop app, [claude.ai/code](https://claude.ai/code), or the **Code** tab in the Claude mobile app.
3. Run:

   ```
   /tabletop-troubleshooting
   ```

That starts a coached drill on Linux and distributed systems at medium difficulty. Everything else is up to the roll until you say otherwise.

## What you can ask for

Add a few words after the command. Plain words are enough. Here's a few examples:

- **Start with the defaults:** a coached drill on Linux or distributed systems, medium difficulty, everything else rolled:

   ```
   /tabletop-troubleshooting
   ```

- **Pick the area.** Everything else is still rolled:

   ```
   /tabletop-troubleshooting networking
   ```

- **Pick how Claude plays:** here, a tutor who explains each output:

   ```
   /tabletop-troubleshooting learn, networking
   ```

- **Set the difficulty:** a clear signal and at most one red herring:

   ```
   /tabletop-troubleshooting learn, networking, easy
   ```

- **Pick the situation:** the outage is already over, and you work out what happened from what's left:

   ```
   /tabletop-troubleshooting databases, forensics
   ```

- **Stack several:** a timed mock interview with a weak signal and evidence you can't fully trust:

   ```
   /tabletop-troubleshooting interview, storage, hard, bad evidence
   ```

- **Bring your own scenario** and skip the roll:

   ```
   /tabletop-troubleshooting learn, DNS resolvers serving stale records after a failover
   ```

To see everything you can ask for before you start, run:

```
/tabletop-troubleshooting options
```

### How Claude plays

| Mode | Claude's role | Scenario weighting | Time box |
| --- | --- | --- | --- |
| `drill` (default) | Coach: supplies commands when you know the goal but not the syntax | Favors what your log rarely covers | None |
| `learn` | Tutor: hints where to look next and explains each output | Favors what your log rarely covers | None |
| `junior` | Junior engineer at the keyboard: you lead, it runs commands and occasionally misreads them | Favors what your log rarely covers | None |
| `interview` | Interviewer: nudges with questions only, never directions | Even across commonly interviewed scenarios | 50 minutes |

`junior` practices running an incident through someone else. Claude plans a few realistic mistakes in its summaries, such as calling high load average CPU saturation when it's really I/O wait. Its raw output is always truthful, so a careful lead can catch every mistake from the evidence.

### The situation

| Add | You get |
| --- | --- |
| `incident` | Something is broken now: a live incident, a recurrence, a handoff or a customer escalation |
| `investigation` | Nothing is on fire: a performance or capacity investigation, post-incident forensics, or a pre-mortem |
| `incident response` | A live incident, and only that |
| `forensics` | The outage is over; work out what happened from what's left |
| `pre-mortem` | You're handed a design and asked how it breaks |
| `handoff` | You take over an incident someone else already touched, and their changes muddy the evidence |
| `customer escalation` | It starts as a support ticket |

### The terrain

| Add | You get |
| --- | --- |
| `storage, some databases` | Mostly storage scenarios, some database ones |
| `networking` | Routing, MTU, load balancers, NAT, firewalls |
| `GPU clusters` | Collective-communication hangs, stragglers, InfiniBand, GPU errors, data loaders |
| `device fleet` | The broken thing runs on remote devices you can't easily reach |
| `managed cloud` | No host shell; provider metrics and logs only |
| `sociotechnical` | Alert fatigue, ownership gaps, eroded trust in CI; you interview people instead of running commands |
| `no security stuff` | Never rolls a security incident |

### Make it harder

| Add | You get |
| --- | --- |
| `hard` | A weak signal, several plausible red herrings, noisy output |
| `bad evidence` | Something you'd rely on is missing, averaged away, delayed or lying |
| `two causes` | Two faults that either need each other or just happen at once |
| `far from the symptom` | The fault sits in the platform, the control plane, a caller, or the monitoring itself |

`easy`, `medium` and `hard` change only how the scenario is written. The rest change what gets rolled.

Before rolling, Claude repeats your choices back in one line, e.g. `Resolved: drill · mostly storage, some databases · medium · excluded: security incidents`, so misreadings get caught early.

## How a session runs

1. **Roll.** `roller.py` picks a value on every axis and prints it **sealed**, as base64. Claude decodes it privately, then checks that decode with `roller.py verify`, which prints only `match` or `mismatch`.
2. **Investigate.** You get a briefing with only what you'd know at the start, then you query the environment turn by turn. `pause` and `resume` freeze and restart the scenario clock.
3. **Reveal.** When you declare a root cause (or give up), Claude asks for a 60-second mitigation and a prevention plan. Then it unseals the roll with `roller.py decode`, so the reveal comes from code rather than memory.
4. **Debrief.** Claude grades how you scoped the blast radius, whether you reasoned with USE (utilization, saturation, errors) or RED (rate, errors, duration), whether you predicted outputs before seeing them, whether you spotted contradictions, and whether you mitigated before root-causing. Command accuracy matters least.
5. **Log.** Claude adds a row to `scenario_log.md`. Future rolls steer away from what you've already done.

## Customizing

Everything lives in the installed skill folder, e.g. `.claude/skills/tabletop-troubleshooting/`:

- `references/option_space.md`: the axes, values, coherence rules and interview subset. It documents its own format; keep the table formats, because the roller parses them.
- `references/scenario_log.md`: your history. It doesn't exist until your first scenario is logged; Claude creates it from `references/scenario_log_example.md`. It stays local: `.gitignore` keeps it out of this repo. Edit or prune rows freely.
- `references/cast.md`: the first names Claude gives the people in a scenario. Add or remove names freely.
- `SKILL.md`: the instructions Claude follows.
- `tools/roller.py`: the roller.

When Claude runs into a combination that's impossible but that no rule caught, it proposes a new rule in the debrief, so the option space grows from real gaps. After any edit to it, validate it (leave out `--log` if you haven't logged a scenario yet):

```
python3 .claude/skills/tabletop-troubleshooting/tools/roller.py check \
  --space .claude/skills/tabletop-troubleshooting/references/option_space.md \
  --log .claude/skills/tabletop-troubleshooting/references/scenario_log.md
```

`check` parses everything, reports unknown codes and rules that constrain an axis rolled before their condition, then stress-tests thousands of rolls in every mode.

## Roller reference

`roller.py` needs only Python 3 and its standard library.

| Command | Purpose |
| --- | --- |
| `roll --space S --log L [--mode M] [--domain D] [--pin P] [--exclude X] [--window N]` | Roll a sealed scenario. `--window` sets how many recent log rows count for coverage (default 20). |
| `verify TOKEN "COORDS"` | Check a decode against a token; prints only `match` or `mismatch` |
| `decode --space S TOKEN` | Unseal a token: coordinates, value names, Writer notes, and a ready-to-paste log row |
| `cast --names N [--count K]` | Shuffle the cast list and print the first K names (default 5) for the people in a scenario |
| `options --space S` | Print the config menu in plain words |
| `check --space S [--log L]` | Validate the option space and stress-test the rules |

The roller rolls axes in a fixed order, applies Hard rules as filters and soft rules as weights, and backtracks when the Hard rules leave no candidates. In coverage modes, it weights each value by `1 / (1 + recent uses)` and never reuses a root-cause layer + mechanism pair from your log.

## Caveats

- **Spoilers are kept out of sight, not made impossible.** Claude Code shows tool output and, depending on your settings, Claude's reasoning. If you expand them mid-scenario you may see more than you meant to.
- **The interview subset is a judgment call** about what typical SRE and Linux troubleshooting interviews ask, not measured data. Adjust it to what your interviews actually look like.
