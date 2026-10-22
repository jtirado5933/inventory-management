"""Scan .vue files for structural, reuse, and performance leads.

Usage:
  python scan_vue.py PATH [PATH ...] [--compare DIR ...] [--min-lines N]

PATH may be a file, a directory, or a glob (quote it on shells that do not expand).
Files in PATH are the scope: leads are reported for them. --compare adds files that are
used only as the other side of cross-file duplication checks and for resolving usage
(for example `--compare client/src` when PATH is a single view).

Read-only. Everything printed is a lead to verify by reading the code, not a verdict.
Regex-based: dynamic components, runtime-built class names, and unusual formatting can
produce false positives, so confirm before reporting.
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

BUILTIN_TAGS = {
    "router-view", "router-link", "transition", "transition-group", "teleport",
    "keep-alive", "component", "slot", "template", "suspense", "routerview",
    "routerlink", "transitiongroup", "keepalive",
}
FUNC_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "else", "watch", "with"}
TRANSITION_CLASS = re.compile(r"-(enter|leave)(-active|-from|-to)?$|^v-")
CALL_IGNORE = {"t", "Math", "Number", "String", "parseInt", "parseFloat", "Boolean", "Array",
               "Object", "JSON", "Date", "if", "typeof"}
SAFE_SORT_SOURCE = ("Object.values(", "Object.keys(", "Object.entries(", ".slice(", ".map(",
                    ".filter(", ".concat(", "Array.from(", "]")


# ---------------------------------------------------------------- text helpers

def blank_comments(s, css=False):
    """Replace comments with spaces (newlines kept) so offsets and line numbers survive."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if not css and c in "'\"`":
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            out.append(s[i:j + 1])
            i = j + 1
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", s[i:j]))
            i = j
        elif not css and s.startswith("//", i):
            j = s.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_close(s, i):
    """Index of the bracket closing s[i], skipping strings; -1 if unbalanced."""
    pairs = {"(": ")", "{": "}", "[": "]"}
    stack, n, j = [], len(s), i
    while j < n:
        c = s[j]
        if c in "'\"`":
            j += 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
        elif c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1]:
            stack.pop()
            if not stack:
                return j
        j += 1
    return -1


def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def short(s, n=70):
    s = norm_ws(s)
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------- SFC parsing

class SFC:
    def __init__(self, path, in_scope):
        self.path = Path(path)
        self.name = self.path.as_posix()
        self.in_scope = in_scope
        text = self.path.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        self.total = len(lines)
        blocks = defaultdict(list)
        i = 0
        while i < len(lines):
            m = re.match(r"<(template|script|style)\b([^>]*)>", lines[i])
            if m:
                kind, attrs = m.group(1), m.group(2)
                j = i + 1
                while j < len(lines) and not lines[j].startswith("</" + kind + ">"):
                    j += 1
                blocks[kind].append({"start": i + 2, "content": "\n".join(lines[i + 1:j]), "attrs": attrs})
                i = j
            i += 1
        tpl = blocks["template"][0] if blocks["template"] else {"start": 1, "content": "", "attrs": ""}
        scr = blocks["script"][0] if blocks["script"] else {"start": 1, "content": "", "attrs": ""}
        self.tpl_start, self.script_start = tpl["start"], scr["start"]
        self.tpl = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), tpl["content"], flags=re.S)
        self.script = blank_comments(scr["content"])
        self.is_setup = "setup" in scr["attrs"]
        self.styles = [{"start": b["start"], "css": blank_comments(b["content"], css=True),
                        "scoped": "scoped" in b["attrs"]} for b in blocks["style"]]
        self.tpl_lines = tpl["content"].count("\n") + 1 if tpl["content"] else 0
        self.script_lines = scr["content"].count("\n") + 1 if scr["content"] else 0
        self.style_lines = sum(b["css"].count("\n") + 1 for b in self.styles)
        self.functions = extract_functions(self.script)

    def tpl_line(self, off):
        return self.tpl_start + self.tpl.count("\n", 0, off)

    def script_line(self, off):
        return self.script_start + self.script.count("\n", 0, off)


def extract_functions(script):
    pats = [
        (re.compile(r"\bfunction\s+(\w+)\s*\([^)]*\)\s*\{"), True),
        (re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>\s*\{"), True),
        (re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=\s*computed\s*\("), False),
        (re.compile(r"^[ \t]+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", re.M), True),
    ]
    found, seen = [], set()
    for rx, brace in pats:
        for m in rx.finditer(script):
            name = m.group(1)
            if name in FUNC_KEYWORDS:
                continue
            open_i = m.end() - 1
            close_i = match_close(script, open_i)
            if close_i < 0 or (name, open_i) in seen:
                continue
            seen.add((name, open_i))
            found.append({"name": name, "off": m.start(), "body": script[open_i + 1:close_i],
                          "computed": not brace})
    return found


# ---------------------------------------------------------------- CSS parsing

def parse_css(css):
    """Leaf rules as (context, selector, declarations dict, char offset)."""
    rules, stack, buf, j, n = [], [], 0, 0, len(css)
    while j < n:
        c = css[j]
        if c == "{":
            raw = css[buf:j]
            sel = raw.strip()
            stack.append(sel)
            nxt_close, nxt_open = css.find("}", j + 1), css.find("{", j + 1)
            if nxt_close != -1 and (nxt_open == -1 or nxt_close < nxt_open):
                ctx = " ".join(s for s in stack[:-1] if s.startswith("@"))
                if not sel.startswith("@") and "@keyframes" not in ctx:
                    decls = {}
                    for d in css[j + 1:nxt_close].split(";"):
                        if ":" in d:
                            k, v = d.split(":", 1)
                            decls[k.strip()] = norm_ws(v)
                    rules.append((ctx, norm_ws(sel), decls, buf + len(raw) - len(raw.lstrip())))
                stack.pop()
                j, buf = nxt_close, nxt_close + 1
            else:
                buf = j + 1
        elif c == "}":
            if stack:
                stack.pop()
            buf = j + 1
        j += 1
    return rules


# ---------------------------------------------------------------- per-file checks

def check_size(f, min_lines):
    leads = []
    if f.tpl_lines > 250:
        leads.append(f"large template ({f.tpl_lines} lines): look for extractable sections")
    if f.script_lines > 400:
        leads.append(f"large script ({f.script_lines} lines): look for logic that belongs in composables")
    if f.total > min_lines and f.style_lines * 2 > f.total:
        leads.append(f"{f.total} lines but {f.style_lines} are style: check for dead or duplicated CSS, not component split")
    return leads


def check_vfor(f):
    leads = []
    for m in re.finditer(r"<[^>]*\bv-for=\"([^\"]*)\"[^>]*>", f.tpl, re.S):
        tag, line = m.group(0), f.tpl_line(m.start())
        key = re.search(r"(?::key|v-bind:key)=\"([^\"]*)\"", tag)
        idx = re.search(r"\(\s*\w+\s*,\s*(\w+)\s*\)", m.group(1))
        if not key:
            leads.append(f"line {line}: v-for without :key (a key on a child may exist; verify)")
        elif idx and re.search(rf"\b{re.escape(idx.group(1))}\b", key.group(1)):
            leads.append(f"line {line}: v-for key uses loop index ({key.group(1)})")
    return leads


def global_components(src_dirs):
    names = set()
    for d in src_dirs:
        for p in Path(d).rglob("*.js"):
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            names.update(re.findall(r"\.component\(\s*['\"]([\w-]+)['\"]", txt))
    return names


def src_root_of(path):
    for parent in Path(path).resolve().parents:
        if parent.name == "src":
            return parent
    return Path(path).resolve().parent


def resolve_import(f, spec):
    base = src_root_of(f.path) / spec[2:] if spec.startswith("@/") else f.path.resolve().parent / spec
    cands = [base] + [Path(str(base) + e) for e in (".vue", ".js")] + [base / "index.js"]
    return any(c.is_file() for c in cands)


def check_components(f, globals_):
    leads = []
    registered, imports = set(), []
    for m in re.finditer(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]", f.script):
        registered.add(m.group(1))
        imports.append((m.group(1), m.group(2), m.start()))
    for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", f.script):
        for part in m.group(1).split(","):
            nm = part.split(" as ")[-1].strip()
            if nm:
                registered.add(nm)
    m = re.search(r"\bcomponents\s*:\s*\{", f.script)
    if m:
        end = match_close(f.script, m.end() - 1)
        registered.update(re.findall(r"(\w+)\s*(?::|,|$)", f.script[m.end():end].replace("\n", " ") + ","))
    norm = lambda s: re.sub(r"[-_]", "", s).lower()
    reg_norm = {norm(r) for r in registered} | {norm(g) for g in globals_}
    for name, spec, off in imports:
        if spec.startswith((".", "@/")) and not resolve_import(f, spec):
            leads.append(f"line {f.script_line(off)}: import '{spec}' does not resolve to a file")
    seen = set()
    for m in re.finditer(r"<([A-Za-z][\w.-]*)", f.tpl):
        tag = m.group(1)
        is_component = tag[0].isupper() or ("-" in tag and tag.islower())
        if not is_component or norm(tag) in BUILTIN_TAGS or norm(tag) in reg_norm or tag in seen:
            continue
        seen.add(tag)
        leads.append(f"line {f.tpl_line(m.start())}: <{tag}> used but not imported/registered "
                     f"(also not registered globally via app.component)")
    return leads


def check_unused_bindings(f):
    leads = []
    if f.is_setup:
        for m in re.finditer(r"^(?:const|let|function)\s+(\w+)([^\n]*)", f.script, re.M):
            name = m.group(1)
            if re.search(r"define(?:Props|Emits|Expose)\s*\(", m.group(2)):
                continue  # compiler macros; the template reads props directly
            used_tpl = re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", f.tpl)
            used_script = len(re.findall(rf"(?<![\w$.]){re.escape(name)}(?![\w$])", f.script)) > 1
            if not used_tpl and not used_script:
                leads.append(f"line {f.script_line(m.start())}: '{name}' declared but never used")
        return leads
    ret = None
    for m in re.finditer(r"\breturn\s*\{", f.script):
        ret = m
    if not ret:
        return leads
    end = match_close(f.script, ret.end() - 1)
    body = f.script[ret.end():end]
    names, depth, cur = [], 0, ""
    for ch in body:
        depth += ch in "({["
        depth -= ch in ")}]"
        if ch == "," and depth == 0:
            names.append(cur)
            cur = ""
        else:
            cur += ch
    names.append(cur)
    unused = []
    for item in names:
        m = re.match(r"\s*(\w+)", item)
        if m and not item.strip().startswith("..."):
            nm = m.group(1)
            if not re.search(rf"(?<![\w$.]){re.escape(nm)}(?![\w$])", f.tpl):
                unused.append(nm)
    if unused:
        leads.append(f"line {f.script_line(ret.start())}: returned from setup but never used in template: "
                     + ", ".join(unused))
    return leads


def check_unused_css(f, corpus_all):
    leads = []
    own = f.tpl + "\n" + f.script
    for st in f.styles:
        corpus = own if st["scoped"] else corpus_all
        unused = []
        for ctx, sel, _, off in parse_css(st["css"]):
            for cls in re.findall(r"\.(-?[_a-zA-Z][\w-]*)", sel):
                if cls in unused or TRANSITION_CLASS.search(cls):
                    continue
                if re.search(r"(?<![\w-])" + re.escape(cls) + r"(?![\w-])", corpus):
                    continue
                prefix = cls.rsplit("-", 1)[0] + "-" if "-" in cls else None
                if prefix and re.search(re.escape(prefix) + r"""(?=['"`$+])""", corpus):
                    continue
                unused.append(cls)
        if unused:
            scope = "scoped style" if st["scoped"] else "global style (checked across scanned files)"
            leads.append(f"{len(unused)} CSS class(es) in {scope} never appear in template/script "
                         f"(may be dynamic): {', '.join('.' + u for u in unused[:12])}"
                         + (" ..." if len(unused) > 12 else ""))
    return leads


def check_script(f):
    leads = []
    s = f.script
    # empty watcher bodies
    for m in re.finditer(r"\bwatch(?:Effect)?\s*\(", s):
        end = match_close(s, m.end() - 1)
        if end > 0 and re.search(r"=>\s*\{\s*\}\s*(?:,\s*\{[^}]*\})?\s*$", s[m.end():end]):
            leads.append(f"line {f.script_line(m.start())}: watcher with an empty body (dead, or a missing refetch)")
    deep = len(re.findall(r"deep\s*:\s*true", s))
    if deep:
        leads.append(f"{deep} deep watcher(s): check what they watch and how large it is")
    nwatch = len(re.findall(r"\bwatch\s*\(", s))
    if nwatch > 3:
        leads.append(f"{nwatch} watchers: check whether some should be computed")
    # in-place sort/reverse on a possibly reactive source
    for m in re.finditer(r"\.(sort|reverse)\s*\(", s):
        before = s[max(0, m.start() - 160):m.start()]
        stmt = before[before.rfind(";") + 1:]  # the receiver chain may span several lines
        if not any(x in stmt for x in SAFE_SORT_SOURCE):
            leads.append(f"line {f.script_line(m.start())}: in-place .{m.group(1)}() on '{short(stmt[-50:], 50)}' "
                         "(safe only if the source is a copy)")
    # timers/listeners without cleanup
    if re.search(r"addEventListener|setInterval|ResizeObserver|IntersectionObserver", s) and \
            not re.search(r"onUnmounted|onBeforeUnmount", s):
        leads.append("listeners/intervals/observers registered but no onUnmounted cleanup")
    # unguarded dates
    if re.search(r"new Date\([^)]*\)\s*\.(?:toISOString|getMonth|getFullYear)|\.getMonth\(\)", s) and \
            not re.search(r"isNaN\(|getTime\(\)", s):
        leads.append("date methods used with no validity check (invalid dates throw in toISOString)")
    # composables called inside nested functions
    for fn in f.functions:
        if fn["name"] != "setup" and re.search(r"\buse[A-Z]\w*\(", fn["body"]):
            leads.append(f"line {f.script_line(fn['off'])}: composable called inside function '{fn['name']}' "
                         "(call composables once at setup top level)")
    # error state never reset
    if re.search(r"\b\w*[eE]rror\.value\s*=\s*[^n=\s]", s) and not re.search(r"\b\w*[eE]rror\.value\s*=\s*null", s):
        leads.append("error ref is assigned but never reset to null (stale error banner after a retry)")
    return leads


def check_fetch(f, all_filter_names):
    """Describe when this file fetches and which shared filters it reads."""
    leads = []
    s = f.script
    api_calls = re.findall(r"\bapi\.(\w+)\(", s)
    if not api_calls:
        return leads
    loaders = {fn["name"] for fn in f.functions if re.search(r"\bapi\.\w+\(", fn["body"])}

    def triggers(arg):
        names = [n for n in loaders if re.search(rf"(?<![\w.]){n}\b", arg)]
        if re.search(r"\bapi\.\w+\(", arg):
            names.append("api.*")
        return names

    mount = []
    for m in re.finditer(r"\bonMounted\s*\(", s):
        end = match_close(s, m.end() - 1)
        mount += triggers(s[m.end():end])
    watches = []
    for m in re.finditer(r"\bwatch\s*\(", s):
        end = match_close(s, m.end() - 1)
        arg = s[m.end():end]
        watches.append((short(arg.split("=>")[0], 40), triggers(arg)))
    parts = [f"{len(api_calls)} api call(s)", "onMounted -> " + (", ".join(sorted(set(mount))) or "none")]
    for src, t in watches:
        parts.append(f"watch({src}) -> " + (", ".join(sorted(set(t))) or "no fetch"))
    leads.append("fetch map: " + "; ".join(parts))
    # loader that toggles a flag gating the whole template
    for fn in f.functions:
        if fn["name"] in loaders:
            for fl in set(re.findall(r"(\w*[lL]oading)\.value\s*=\s*true", fn["body"])):
                if re.search(rf"v-if=\"\s*{fl}\s*\"", f.tpl) and any(fn["name"] in t for _, t in watches):
                    leads.append(f"'{fl}' gates the template with v-if and '{fn['name']}' is re-run by a watcher: "
                                 "every refetch unmounts and rebuilds the view")
    m = re.search(r"const\s*\{([^}]*)\}\s*=\s*useFilters\(\)", s)
    if m and all_filter_names:
        used = {x.split(":")[0].strip() for x in m.group(1).split(",") if x.strip()}
        if "getCurrentFilters" not in used:
            unused = [n for n in all_filter_names if n not in used]
            if unused:
                leads.append(f"reads {len(all_filter_names) - len(unused)} of {len(all_filter_names)} shared filters "
                             f"and never calls getCurrentFilters (not read: {', '.join(unused)})")
    return leads


def check_template(f, min_calls=8):
    leads = []
    exprs = [m.group(1) for m in re.finditer(r"\{\{(.*?)\}\}", f.tpl, re.S)]
    exprs += [m.group(1) for m in re.finditer(r"(?:^|\s)(?::|v-)[\w:.-]*=\"([^\"]*)\"", f.tpl)]
    counts = defaultdict(int)
    for e in exprs:
        for m in re.finditer(r"(?<![\w.$])([A-Za-z_]\w*)\s*\(", e):
            if m.group(1) not in CALL_IGNORE:
                counts[m.group(1)] += 1
    heavy = sorted(((c, n) for n, c in counts.items() if c >= min_calls), reverse=True)[:3]
    for c, n in heavy:
        leads.append(f"{n}() called {c} times in template: re-runs on every render, check per-call cost "
                     "(lookup tables rebuilt, Date parsing)")
    if re.search(r"\.(?:filter|map|reduce|sort)\s*\(", "\n".join(exprs)):
        leads.append("array filter/map/reduce/sort inside template expressions: move to computed")
    uses_i18n = re.search(r"useI18n|\$t\(|(?<![\w.])t\(", f.script + f.tpl)
    if uses_i18n:
        blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
        text = re.sub(r"\{\{.*?\}\}", blank, f.tpl, flags=re.S)
        # replace each tag (quote-aware, so '>' inside attribute expressions is safe) with a delimiter
        marked = re.sub(r"""<[A-Za-z/](?:"[^"]*"|'[^']*'|[^>"'])*>""",
                        lambda m: "\x01" + blank(m)[1:], text)
        hard = []
        for m in re.finditer(r"[^\x01]+", marked):
            t = norm_ws(re.sub(r"&\w+;", " ", m.group(0)))
            if re.search(r"[A-Za-z]{3,}", t):
                lead_ws = len(m.group(0)) - len(m.group(0).lstrip())
                hard.append((f.tpl_line(m.start() + lead_ws), t))
        for m in re.finditer(r"\s(?:placeholder|title|alt|aria-label)=\"([^\"{}]*[A-Za-z]{3,}[^\"{}]*)\"", text):
            hard.append((f.tpl_line(m.start(1)), m.group(1)))
        if hard:
            ex = "; ".join(f"{ln}: \"{short(t, 30)}\"" for ln, t in hard[:4])
            leads.append(f"{len(hard)} hardcoded user-facing string(s) in a file that uses i18n (e.g. {ex})")
    return leads


# ---------------------------------------------------------------- cross-file checks

def template_duplicates(files, min_lines=4):
    per_file, index = {}, defaultdict(dict)
    for f in files:
        rows = []
        for i, l in enumerate(f.tpl.split("\n")):
            t = norm_ws(l)
            if t:
                rows.append((f.tpl_start + i, t))
        per_file[f.name] = rows
        for i in range(len(rows) - min_lines + 1):
            win = "\n".join(t for _, t in rows[i:i + min_lines])
            if len(win) > 80:
                index[win].setdefault(f.name, i)
    groups = defaultdict(list)
    for win, pos in index.items():
        if len(pos) > 1:
            groups[tuple(sorted(pos))].append(pos)
    out = []
    for fileset, items in groups.items():
        anchor = fileset[0]
        items.sort(key=lambda p: p[anchor])
        run = [items[0]]
        runs = []
        for p in items[1:]:
            prev = run[-1]
            if all(p[x] == prev[x] + 1 for x in fileset):
                run.append(p)
            else:
                runs.append(run)
                run = [p]
        runs.append(run)
        for r in runs:
            length = len(r) + min_lines - 1
            spans = []
            for x in fileset:
                rows = per_file[x]
                spans.append(f"{Path(x).name}:{rows[r[0][x]][0]}-{rows[r[0][x] + length - 1][0]}")
            first = per_file[anchor][r[0][anchor]][1]
            out.append((length, spans, first))
    out.sort(key=lambda o: -o[0])
    return out


def style_duplicates(files):
    ident = defaultdict(set)
    by_sel = defaultdict(dict)
    for f in files:
        for st in f.styles:
            for ctx, sel, decls, off in parse_css(st["css"]):
                key = (ctx, sel)
                sig = tuple(sorted(decls.items()))
                ident[(key, sig)].add(f.name)
                by_sel[key].setdefault(f.name, decls)
    shared = defaultdict(list)
    for (key, sig), fs in ident.items():
        if len(fs) > 1:
            shared[tuple(sorted(fs))].append(key[1])
    drift = []
    for key, per_file in by_sel.items():
        sigs = defaultdict(list)
        for fn, d in per_file.items():
            sigs[tuple(sorted(d.items()))].append(fn)
        if len(sigs) > 1 and any(len(v) > 1 for v in sigs.values()):
            majority = max(sigs.values(), key=len)
            maj = dict(per_file[majority[0]])
            for fn in per_file:
                if fn in majority:
                    continue
                d = per_file[fn]
                diffs = [f"{p}: {d.get(p, '(unset)')} vs {maj.get(p, '(unset)')}"
                         for p in sorted(set(d) | set(maj)) if d.get(p) != maj.get(p)]
                drift.append((len(majority), f"{key[1]} in {Path(fn).name} differs from {len(majority)} other file(s): "
                              + "; ".join(diffs[:4]) + (" ..." if len(diffs) > 4 else "")))
    drift.sort(key=lambda x: -x[0])
    return sorted(shared.items(), key=lambda kv: -len(kv[1])), [d for _, d in drift]


def script_duplicates(files):
    by_body, by_name = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for f in files:
        for fn in f.functions:
            body = norm_ws(fn["body"])
            if len(body) < 40 or fn["name"] == "setup":
                continue
            loc = (f.name, f.script_line(fn["off"]))
            by_body[body].append((fn["name"], loc))
            by_name[fn["name"]][body].append(loc)
    same = []
    for body, items in by_body.items():
        if len({loc[0] for _, loc in items}) > 1:
            names = sorted({n for n, _ in items})
            locs = ", ".join(f"{Path(fl).name}:{ln}" for _, (fl, ln) in items)
            same.append((len(items), f"{'/'.join(names)} ({len(norm_ws(body))} chars): {locs}"))
    same.sort(key=lambda x: -x[0])
    drift = []
    for name, bodies in by_name.items():
        files_with = {loc[0] for locs in bodies.values() for loc in locs}
        if len(bodies) > 1 and len(files_with) > 1:
            locs = ", ".join(f"{Path(l[0]).name}:{l[1]}" for locs_ in bodies.values() for l in locs_)
            drift.append(f"{name}: {len(bodies)} different bodies in {locs}")
    return [s for _, s in same], drift


# ---------------------------------------------------------------- main

def collect(paths):
    out = []
    for p in paths:
        if any(ch in p for ch in "*?["):
            out += [Path(x) for x in glob.glob(p, recursive=True) if x.endswith(".vue")]
        elif os.path.isdir(p):
            out += sorted(Path(p).rglob("*.vue"))
        elif os.path.isfile(p):
            out.append(Path(p))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--compare", nargs="*", default=[], help="extra dirs/files for cross-file checks only")
    ap.add_argument("--min-lines", type=int, default=400)
    args = ap.parse_args()

    scope = collect(args.paths)
    if not scope:
        print("No .vue files found for: " + " ".join(args.paths), file=sys.stderr)
        return 1
    scope_set = {p.resolve() for p in scope}
    extra = [p for p in collect(args.compare) if p.resolve() not in scope_set]
    files = [SFC(p, True) for p in scope] + [SFC(p, False) for p in extra]
    in_scope = [f for f in files if f.in_scope]

    src_dirs = {src_root_of(p) for p in scope + extra}
    globals_ = global_components(src_dirs)
    filter_names = []
    for d in src_dirs:
        for p in Path(d).rglob("useFilters.js"):
            filter_names = re.findall(r"^(?:const|let)\s+(\w+)\s*=\s*ref\(", p.read_text(encoding="utf-8"), re.M)
    corpus_all = "\n".join(f.tpl + "\n" + f.script for f in files)

    print("Columns: lines=total, tmpl/script/style=lines per block, watch/comp=counts of watch()/computed()\n")
    print(f"{'file':46} {'lines':>5} {'tmpl':>5} {'script':>6} {'style':>5} {'watch':>5} {'comp':>4}")
    for f in sorted(in_scope, key=lambda x: -x.total):
        n_watch = len(re.findall(r"\bwatch\s*\(", f.script))
        n_comp = len(re.findall(r"computed\s*\(", f.script))
        print(f"{f.name:46} {f.total:>5} {f.tpl_lines:>5} {f.script_lines:>6} {f.style_lines:>5} "
              f"{n_watch:>5} {n_comp:>4}")

    print("\nPer-file leads:")
    any_lead = False
    for f in in_scope:
        leads = (check_size(f, args.min_lines) + check_components(f, globals_) + check_vfor(f)
                 + check_unused_bindings(f) + check_unused_css(f, corpus_all) + check_script(f)
                 + check_template(f) + check_fetch(f, filter_names))
        if leads:
            any_lead = True
            print(f"  {f.name}")
            for lead in leads:
                print(f"    - {lead}")
    if not any_lead:
        print("  none")

    print("\nCross-file duplication (leads only where at least one file is in scope):")
    scoped_names = {f.name for f in in_scope}
    scoped_base = {Path(n).name for n in scoped_names}
    touch = lambda names: any(n in scoped_names for n in names)
    if len(files) < 2:
        print("  only one file scanned; pass --compare DIR to look for duplication elsewhere")
        return 0

    print("  Template (runs of 4+ identical lines):")
    rows = [(n, sp, first) for n, sp, first in template_duplicates(files)
            if any(s.split(":")[0] in scoped_base for s in sp)]
    for n, sp, first in rows[:12]:
        print(f"    {n} lines: {', '.join(sp)}  | {short(first, 60)}")
    if not rows:
        print("    none")

    shared, drift = style_duplicates(files)
    print("  Style (identical CSS rules across files):")
    shown = 0
    for fileset, sels in shared:
        if touch(fileset) and shown < 8:
            shown += 1
            ex = ", ".join(sels[:4]) + (" ..." if len(sels) > 4 else "")
            print(f"    {len(sels)} identical rule(s) in: {', '.join(Path(x).name for x in fileset)} (e.g. {ex})")
    if not shown:
        print("    none")
    print("  Style drift (same selector copied, values differ):")
    drift = [d for d in drift if any(Path(n).name in d for n in scoped_names)]
    for d in drift[:12]:
        print(f"    {d}")
    if not drift:
        print("    none")

    same, sdrift = script_duplicates(files)
    print("  Script (identical function bodies in 2+ files):")
    same = [s for s in same if any(Path(n).name in s for n in scoped_names)]
    for s in same[:12]:
        print(f"    {s}")
    if not same:
        print("    none")
    print("  Script drift (same function name, different bodies):")
    sdrift = [s for s in sdrift if any(Path(n).name in s for n in scoped_names)]
    for s in sdrift[:8]:
        print(f"    {s}")
    if not sdrift:
        print("    none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
