#!/usr/bin/env python3
"""Scenario roller for troubleshooting tabletop drills.

Reads three Markdown exports:
  - the Troubleshooting Scenario Option Space (axes, values, rules, interview subset)
  - the Troubleshooting Scenario Cast (first names for people in a scenario)
  - the Troubleshooting Scenario Log (past scenarios' coordinates)

Commands:
  roll     Roll a scenario and print it sealed (base64), so nothing is spoiled.
  decode   Unseal a rolled token: coordinates, value names, writer notes, log row.
  verify   Check a decoded coordinate string against a token; prints only match/mismatch.
  cast     Print five names, shuffled from a cast list, for the people in a scenario.
  options  Print the menu of domains and axes for building a session config.
  check    Validate the option space and stress-test the rules with many rolls.

Examples:
  python3 roller.py roll --space option_space.md --log scenario_log.md --mode drill --domain D2:3,D4:1
  python3 roller.py roll --space option_space.md --log scenario_log.md --pin E7 --exclude D17,X5
  python3 roller.py decode --space option_space.md <token>
  python3 roller.py verify <token> "D2 · R5 W1 ..."
  python3 roller.py cast --names cast.md
  python3 roller.py options --space option_space.md
  python3 roller.py check --space option_space.md --log scenario_log.md
"""

import argparse
import base64
import random
import re
import sys
from collections import Counter

# Roll order. D comes from config; A shapes everything else, so it rolls next.
ORDER = ["D", "A", "R", "W", "S", "G", "E", "F",
         "L", "M", "T", "N", "C", "I", "Y", "B", "O", "X"]
# Display order, matching the log's coordinate format.
DISPLAY = [["D"], ["R", "W", "S", "G", "E", "F"],
           ["L", "M", "T", "N", "C", "I"], ["Y", "B", "O", "A", "X"]]
MODES = ["drill", "learn", "junior", "interview"]
RULE_TYPES = {"Hard", "Prefer", "Avoid", "Writer"}
SOFT_FACTOR = {"Prefer": 3.0, "Avoid": 0.25}
DEFAULT_DOMAIN = "D1,D2"
DEFAULT_WINDOW = 20

CODE_RE = re.compile(r"^([A-Z])(\d+)$")
CLAUSE_RE = re.compile(r"^([A-Z]) in \{([^}]*)\}$")


class SpaceError(Exception):
    pass


# ---------------------------------------------------------------- parsing

def split_row(line):
    """Cells of a Markdown table row, or None for separator / non-table lines."""
    line = line.strip()
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.strip("|").split("|")]
    if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
        return None
    return cells


def unquote(cell):
    cell = cell.strip()
    if len(cell) >= 2 and cell[0] == "`" and cell[-1] == "`":
        return cell[1:-1].strip()
    return cell


def parse_set(text):
    text = unquote(text).strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise SpaceError(f"expected {{values}}, got {text!r}")
    return {v.strip() for v in text[1:-1].split(",") if v.strip()}


def parse_condition(text):
    """`A in {..} and B in {..}` -> ("and"|"or", [(axis, set), ...])."""
    text = unquote(text)
    has_and, has_or = " and " in text, " or " in text
    if has_and and has_or:
        raise SpaceError(f"mixing 'and' and 'or' is not supported: {text!r}")
    joiner = "and" if has_and else "or"
    clauses = []
    for part in text.split(f" {joiner} "):
        m = CLAUSE_RE.match(part.strip())
        if not m:
            raise SpaceError(f"bad clause {part!r} in {text!r}")
        clauses.append((m.group(1), {v.strip() for v in m.group(2).split(",") if v.strip()}))
    return joiner, clauses


def parse_rule(if_cell, then_cell, kind):
    rule = {"kind": kind, "if_text": unquote(if_cell), "then_text": unquote(then_cell)}
    rule["joiner"], rule["clauses"] = parse_condition(if_cell)
    then = unquote(then_cell)
    if kind == "Hard":
        m = CLAUSE_RE.match(then)
        if m:
            rule["op"] = "restrict"
            rule["axis"] = m.group(1)
            rule["values"] = {v.strip() for v in m.group(2).split(",") if v.strip()}
        elif then.startswith("skip ") or then.startswith("extra "):
            op, rest = then.split(" ", 1)
            rule["op"] = op
            rule["axes"] = [a.strip() for a in rest.split(",") if a.strip()]
        else:
            raise SpaceError(f"bad Hard rule 'Then': {then!r}")
    elif kind in SOFT_FACTOR:
        rule["op"] = "weight"
        rule["values"] = parse_set(then)
        rule["factor"] = SOFT_FACTOR[kind]
    else:
        rule["op"] = "writer"
    return rule


def parse_space(md):
    space = {"values": {}, "names": {}, "axis_names": {"D": "Domain"},
             "rules": [], "interview": {}}
    section = ""
    for raw in md.splitlines():
        line = raw.strip()
        h = re.match(r"^#{2,3}\s+(.*)$", line)
        if h:
            section = h.group(1)
            ah = re.match(r"^([A-Z])\s+[—-]\s+(.+)$", section)
            if ah:
                space["axis_names"][ah.group(1)] = ah.group(2)
            continue
        cells = split_row(line)
        if not cells:
            continue
        first = unquote(cells[0])
        if section.startswith("Interview subset"):
            if re.fullmatch(r"[A-Z]", first) and len(cells) >= 2:
                space["interview"][first] = parse_set(cells[1])
            continue
        if len(cells) >= 3 and cells[-1] in RULE_TYPES:
            space["rules"].append(parse_rule(cells[0], cells[1], cells[-1]))
            continue
        m = CODE_RE.match(first)
        if m and len(cells) >= 2:
            space["values"].setdefault(m.group(1), []).append(first)
            space["names"][first] = cells[1]
    validate_space(space)
    return space


def validate_space(space):
    problems = []
    known = set(space["names"])
    for axis in ORDER:
        if not space["values"].get(axis):
            problems.append(f"axis {axis} has no values")

    def check_codes(codes, where):
        for c in codes:
            if c not in known:
                problems.append(f"{where}: unknown value {c}")

    pos = {a: i for i, a in enumerate(ORDER)}
    for r in space["rules"]:
        where = f"rule [{r['if_text']} -> {r['then_text']}]"
        if_axes = [a for a, _ in r["clauses"]]
        for a, vals in r["clauses"]:
            check_codes(vals, where)
            if a not in pos:
                problems.append(f"{where}: unknown axis {a}")
        last_if = max(pos.get(a, -1) for a in if_axes)
        targets = []
        if r["op"] == "restrict":
            check_codes(r["values"], where)
            targets = [r["axis"]]
        elif r["op"] in ("skip",):
            targets = r["axes"]
        elif r["op"] == "weight":
            check_codes(r["values"], where)
            targets = sorted({v[0] for v in r["values"]})
        for t in targets:
            if t not in pos:
                problems.append(f"{where}: unknown axis {t}")
            elif pos[t] <= last_if:
                problems.append(f"{where}: constrains {t}, which rolls before its If clauses")
    for axis, vals in space["interview"].items():
        check_codes(vals, f"interview subset {axis}")
    if problems:
        raise SpaceError("option space problems:\n  " + "\n  ".join(problems))


def parse_coords(text):
    """Coordinate string -> {axis: [codes]}; '?' values are dropped."""
    out = {}
    for tok in re.split(r"[\s·|]+", text.strip()):
        if not tok:
            continue
        for part in tok.split("+"):
            m = re.fullmatch(r"([A-Z])(\d+|\?)", part)
            if not m:
                raise SpaceError(f"bad coordinate token {part!r} in {text!r}")
            if m.group(2) != "?":
                out.setdefault(m.group(1), []).append(part)
    return out


def parse_log(md):
    rows = []
    for raw in md.splitlines():
        cells = split_row(raw)
        if not cells:
            continue
        for c in cells:
            if c.startswith("`") and "·" in c:
                rows.append(parse_coords(unquote(c)))
                break
    return rows  # newest first, as the log is kept


# ---------------------------------------------------------------- rolling

def fires(rule, assignment):
    results = []
    for axis, vals in rule["clauses"]:
        got = assignment.get(axis)
        results.append(bool(got) and any(v in vals for v in got))
    return all(results) if rule["joiner"] == "and" else any(results)


def weighted_order(cands, weights, rng):
    """Weighted shuffle without replacement (Efraimidis-Spirakis)."""
    keyed = []
    for c in cands:
        w = weights[c]
        if w <= 0:
            continue
        keyed.append((rng.random() ** (1.0 / w), c))
    keyed.sort(reverse=True)
    return [c for _, c in keyed]


class Roller:
    def __init__(self, space, log_rows, mode, domain_weights, pins, excludes,
                 window, rng):
        self.space, self.mode, self.rng = space, mode, rng
        self.domain_weights = domain_weights
        self.pins, self.excludes = pins, excludes
        recent = log_rows[:window]
        self.counts = Counter(c for row in recent for codes in row.values() for c in codes)
        self.lm_pairs = {(l, m) for row in log_rows
                         for l in row.get("L", []) for m in row.get("M", [])}

    def skipped(self, axis, assignment):
        return any(r["op"] == "skip" and axis in r["axes"] and fires(r, assignment)
                   for r in self.space["rules"])

    def candidates(self, axis, assignment):
        if axis in self.pins:
            cands = list(self.pins[axis])
        elif axis == "D":
            cands = [d for d in self.domain_weights if d not in self.excludes]
        else:
            cands = [v for v in self.space["values"][axis] if v not in self.excludes]
        for r in self.space["rules"]:
            if r["op"] == "restrict" and r["axis"] == axis and fires(r, assignment):
                cands = [c for c in cands if c in r["values"]]
        if axis not in self.pins:
            cands = self.prefer_fresh_pairs(axis, cands, assignment)
        return cands

    def prefer_fresh_pairs(self, axis, cands, assignment):
        """Coverage modes never reuse a logged L + M pair, unless nothing else fits."""
        if self.mode == "interview" or axis not in ("L", "M"):
            return cands
        other = assignment.get("M" if axis == "L" else "L", [])
        key = (lambda c, o: (c, o)) if axis == "L" else (lambda c, o: (o, c))
        fresh = [c for c in cands if not any(key(c, o) in self.lm_pairs for o in other)]
        return fresh or cands

    def weights(self, axis, cands, assignment):
        w = {}
        for c in cands:
            if axis == "D":
                w[c] = self.domain_weights.get(c, 1.0)
            elif self.mode == "interview":
                w[c] = 1.0
            else:
                w[c] = 1.0 / (1 + self.counts[c])
        for r in self.space["rules"]:
            if r["op"] == "weight" and fires(r, assignment):
                for c in cands:
                    if c in r["values"]:
                        w[c] *= r["factor"]
        return w

    def ordered(self, axis, cands, assignment):
        w = self.weights(axis, cands, assignment)
        if self.mode == "interview" and axis in self.space["interview"]:
            subset = self.space["interview"][axis]
            inside = [c for c in cands if c in subset]
            outside = [c for c in cands if c not in subset]
            # Hard rules may force values outside the subset; use them only then.
            return weighted_order(inside, w, self.rng) + weighted_order(outside, w, self.rng)
        return weighted_order(cands, w, self.rng)

    def add_extras(self, assignment, applied):
        for i, r in enumerate(self.space["rules"]):
            if r["op"] != "extra" or i in applied or not fires(r, assignment):
                continue
            applied.add(i)
            for axis in r["axes"]:
                have = assignment.get(axis, [])
                cands = [v for v in self.space["values"][axis]
                         if v not in have and v not in self.excludes]
                cands = self.prefer_fresh_pairs(axis, cands, assignment)
                order = self.ordered(axis, cands, assignment)
                if order:
                    assignment[axis] = have + [order[0]]

    def solve(self, budget=20000):
        """Roll every axis in order, backtracking when Hard rules leave no
        candidates. Gives up after `budget` steps, which only happens when
        pins and exclusions contradict the rules."""
        self.budget = budget
        return self._solve(0, {}, set())

    def _solve(self, i, assignment, applied):
        self.budget -= 1
        if self.budget < 0:
            return None
        if i == len(ORDER):
            return assignment
        axis = ORDER[i]
        if self.skipped(axis, assignment):
            nxt = dict(assignment)
            nxt[axis] = []
            return self._solve(i + 1, nxt, set(applied))
        for choice in self.ordered(axis, self.candidates(axis, assignment), assignment):
            nxt = dict(assignment)
            nxt[axis] = [choice]
            nxt_applied = set(applied)
            self.add_extras(nxt, nxt_applied)
            result = self._solve(i + 1, nxt, nxt_applied)
            if result is not None:
                return result
            if self.budget < 0:
                return None
        return None  # backtrack


def format_coords(assignment, sep=" · "):
    groups = []
    for group in DISPLAY:
        toks = ["+".join(assignment[a]) for a in group if assignment.get(a)]
        if toks:
            groups.append(" ".join(toks))
    return sep.join(groups)


def seal(assignment):
    return base64.b64encode(format_coords(assignment, " | ").encode()).decode()


def unseal(token):
    return base64.b64decode(token.strip()).decode()


# ---------------------------------------------------------------- config

def parse_codes(text):
    return [t for t in re.split(r"[\s,]+", text or "") if t]


def parse_domain(text, space):
    weights = {}
    for tok in parse_codes(text):
        code, _, w = tok.partition(":")
        if code not in space["values"]["D"]:
            raise SpaceError(f"unknown domain {code}")
        weights[code] = float(w) if w else 1.0
    if not weights:
        raise SpaceError("no domain given")
    return weights


def parse_pins(text, space):
    pins = {}
    for code in parse_codes(text):
        if code not in space["names"]:
            raise SpaceError(f"unknown pin {code}")
        pins.setdefault(code[0], []).append(code)
    return pins


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- commands

def cmd_roll(args):
    space = parse_space(load(args.space))
    log_rows = parse_log(load(args.log)) if args.log else []
    rng = random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    excludes = set(parse_codes(args.exclude))
    for code in excludes:
        if code not in space["names"]:
            raise SpaceError(f"unknown exclusion {code}")
    roller = Roller(space, log_rows, args.mode, parse_domain(args.domain, space),
                    parse_pins(args.pin, space), excludes, args.window, rng)
    result = roller.solve()
    if result is None:
        raise SpaceError("no scenario satisfies these pins and exclusions together")
    print("Rolled. Sealed scenario (decode only at debrief):")
    print(seal(result))


def parse_cast(md):
    """Return the names from a Markdown bulleted list, in order, without duplicates."""
    names = set()
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        name = line[2:].strip()
        if name:
            names.add(name)
    return names


def cmd_cast(args):
    names = list(parse_cast(load(args.names)))
    if len(names) < args.count:
        raise SpaceError(f"cast list has {len(names)} names; need at least {args.count}")
    rng = random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    rng.shuffle(names)
    print("Cast (use these names, in this order, for everyone in the scenario):")
    for name in names[:args.count]:
        print(f"  {name}")


def cmd_decode(args):
    space = parse_space(load(args.space))
    coords = unseal(args.token)
    assignment = parse_coords(coords)
    print("Coordinates:", format_coords(assignment))
    print()
    for group in DISPLAY:
        for axis in group:
            for code in assignment.get(axis, []):
                print(f"  {code:<4} {space['axis_names'].get(axis, axis)}: {space['names'][code]}")
    notes = [r["then_text"] for r in space["rules"]
             if r["op"] == "writer" and fires(r, assignment)]
    if notes:
        print("\nWriter notes:")
        for n in notes:
            print("  -", n)
    print("\nLog row (fill in date, scenario and root cause):")
    print(f"| <YYYY/MM/DD> | <scenario> | `{format_coords(assignment)}` | <root cause> |")


def cmd_verify(args):
    """Check a mental decode against the token without printing either."""
    try:
        sealed = parse_coords(unseal(args.token))
        guess = parse_coords(args.coords)
    except (ValueError, SpaceError):
        print("mismatch")
        return 1
    same = sealed == guess
    print("match" if same else "mismatch")
    return 0 if same else 1


def cmd_options(args):
    space = parse_space(load(args.space))
    print("Modes: interview, drill (default), learn, junior\n")
    print("Domains:")
    for code in space["values"]["D"]:
        print(f"  {code:<4} {space['names'][code]}")
    print("\nAxes you can pin or exclude (examples):")
    for axis in ORDER[1:]:
        vals = space["values"][axis]
        sample = ", ".join(f"{v} {space['names'][v]}" for v in vals[:3])
        print(f"  {axis} {space['axis_names'].get(axis, axis)} ({len(vals)} values): {sample}, ...")


def cmd_check(args):
    space = parse_space(load(args.space))
    log_rows = parse_log(load(args.log)) if args.log else []
    print(f"Parsed {sum(len(v) for v in space['values'].values())} values on "
          f"{len(space['values'])} axes, {len(space['rules'])} rules, "
          f"{len(space['interview'])} interview axes, {len(log_rows)} log rows.")
    rng = random.Random(args.seed)
    failures = 0
    for mode in MODES:
        for n in range(args.n):
            roller = Roller(space, log_rows, mode,
                            {d: 1.0 for d in space["values"]["D"]}, {}, set(),
                            DEFAULT_WINDOW, rng)
            result = roller.solve()
            if result is None:
                failures += 1
                continue
            for r in space["rules"]:
                if not fires(r, result):
                    continue
                if r["op"] == "restrict" and result.get(r["axis"]) and \
                        result[r["axis"]][0] not in r["values"]:
                    failures += 1
                    print("VIOLATION", r["if_text"], "->", r["then_text"], format_coords(result))
                if r["op"] == "skip" and any(result.get(a) for a in r["axes"]):
                    failures += 1
                    print("VIOLATION", r["if_text"], "->", r["then_text"], format_coords(result))
            if parse_coords(unseal(seal(result))) != {k: v for k, v in result.items() if v}:
                failures += 1
                print("ROUND-TRIP FAILURE", format_coords(result))
    print(f"{args.n} rolls per mode x {len(MODES)} modes: {failures} failures")
    return 1 if failures else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("roll", help="roll a sealed scenario")
    r.add_argument("--space", required=True)
    r.add_argument("--log")
    r.add_argument("--mode", choices=MODES, default="drill")
    r.add_argument("--domain", default=DEFAULT_DOMAIN, help='e.g. "D2:3,D4:1"')
    r.add_argument("--pin", default="", help='e.g. "E7,A3"')
    r.add_argument("--exclude", default="", help='e.g. "D17,X5"')
    r.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    r.add_argument("--seed", type=int, help="for testing only; omit for real randomness")
    r.set_defaults(func=cmd_roll)

    n = sub.add_parser("cast", help="pick names for the people in a scenario")
    n.add_argument("--names", required=True, help="Markdown file with one name per bullet")
    n.add_argument("--count", type=int, default=5)
    n.add_argument("--seed", type=int, help="for testing only; omit for real randomness")
    n.set_defaults(func=cmd_cast)

    d = sub.add_parser("decode", help="unseal a token at debrief")
    d.add_argument("--space", required=True)
    d.add_argument("token")
    d.set_defaults(func=cmd_decode)

    v = sub.add_parser("verify", help="check a decode without revealing it")
    v.add_argument("token")
    v.add_argument("coords")
    v.set_defaults(func=cmd_verify)

    o = sub.add_parser("options", help="print the config menu")
    o.add_argument("--space", required=True)
    o.set_defaults(func=cmd_options)

    c = sub.add_parser("check", help="validate and stress-test")
    c.add_argument("--space", required=True)
    c.add_argument("--log")
    c.add_argument("--n", type=int, default=2000)
    c.add_argument("--seed", type=int, default=0)
    c.set_defaults(func=cmd_check)

    args = p.parse_args(argv)
    try:
        return args.func(args) or 0
    except SpaceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
