"""unitcalcs_tex -- render clean Calcpad-like calc blocks as handcalcs worked LaTeX.

Write only assignment lines with bare unit names (kN, m, MPa, ...) and optional
'# annotation'. Values persist across blocks in one document, so a quantity defined
in an early chapter can be used in a later one. Input-value lines render as
parameters; lines that reference other variables render in full
symbolic -> substituted -> result form, with units carried by forallpeople.
"""
import re, os, glob
import forallpeople
import handcalcs.handcalcs as hc

forallpeople.environment('structural')
import forallpeople as u
UNIT_NS = {n: getattr(u, n) for n in dir(u) if isinstance(getattr(u, n), u.Physical)}

# forallpeople's 'structural' environment ships a fixed list (m, mm, kN, MPa, ...).
# Add the everyday engineering units it omits, so "3 cm" or "12 kNm" just work.
def _extra_units():
    m, N, kN, kg, s, Pa, J, W = (UNIT_NS[k] for k in ("m", "N", "kN", "kg", "s", "Pa", "J", "W"))
    e = {
        "cm": 0.01 * m, "dm": 0.1 * m, "km": 1000 * m, "um": 1e-6 * m, "\u00b5m": 1e-6 * m,
        "g": 0.001 * kg, "t": 1000 * kg,
        "kNm": kN * m, "MNm": 1e6 * N * m, "Ncm": N * 0.01 * m,
        "kJ": 1000 * J, "kW": 1000 * W, "MW": 1e6 * W,
        "hPa": 100 * Pa, "bar": 1e5 * Pa, "N_mm2": N / (0.001 * m) ** 2,
        "h": 3600 * s, "Hz": 1 / s, "kHz": 1000 / s,
    }
    return {k: v for k, v in e.items() if k not in UNIT_NS}

UNIT_NS.update(_extra_units())
_UNIT_RE = '|'.join(sorted(map(re.escape, UNIT_NS), key=len, reverse=True))

import math as _math


MATH_NS = {
    # logs: log10/lg (German) render as \\log_{10}; log/ln are natural
    # log = BASE 10, following the English engineering convention (and how German
    # books print log in level/sound-insulation formulas). NOTE this differs from
    # Python's math.log, which is natural -- natural log is ln() or log_e() here.
    "log": _math.log10, "log10": _math.log10, "lg": _math.log10,   # base 10
    "LOGTENQQ": _math.log10,   # internal alias for source 'log' (see _encode_log)
    "ln": _math.log, "log_e": _math.log,                            # natural
    "log2": _math.log2, "ld": _math.log2, "lb": _math.log2,         # base 2
    "exp": _math.exp, "sqrt": _math.sqrt,
    "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
    "asin": _math.asin, "acos": _math.acos, "atan": _math.atan, "atan2": _math.atan2,
    "sinh": _math.sinh, "cosh": _math.cosh, "tanh": _math.tanh,
    "radians": _math.radians, "degrees": _math.degrees,
    "floor": _math.floor, "ceil": _math.ceil,
    "abs": abs, "min": min, "max": max, "round": round, "sum": sum,
    "pi": _math.pi, "e": _math.e,
}

def _base_ns():
    ns = dict(UNIT_NS)
    ns.update(MATH_NS)
    return ns

_SESSION = _base_ns()   # persistent namespace for the whole document
_USER_VARS = set()         # user-defined names seen so far (excludes units)

def reset():
    _SESSION.clear(); _SESSION.update(_base_ns()); _USER_VARS.clear()
    _reset_blocks()

_COMMA_TOKEN = "QQCQQ"
_PRIME_TOKEN = "QQPQQ"
# identifier with one or more comma-separated subscripts, e.g. R_w,ges  L_n,w  R_w,R
_POW_MINUS_RE = re.compile(r"\*\*\s*-\s*")

def _fix_pow_minus(src):
    """Parenthesise a unary minus that directly follows ** :  10**-x  ->  10**(-x).

    handcalcs cannot parse an exponent that starts with a bare minus; it silently drops
    the surrounding function call and renders things like "<built-in function log10>".
    The two forms are mathematically identical (** binds tighter than the following
    operator), so the rewrite is safe and only affects how the line is parsed.
    """
    out = []
    for line in src.splitlines():
        code, sep, comment = line.partition("#")
        pos = 0
        while True:
            m = _POW_MINUS_RE.search(code, pos)
            if not m:
                break
            start = m.end()                      # first char of the exponent operand
            if start >= len(code):
                break
            if code[start] == "(":               # balanced group: 10**-(a+b)
                depth, j = 0, start
                while j < len(code):
                    if code[j] == "(":
                        depth += 1
                    elif code[j] == ")":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                end = j
            else:                                # identifier or number
                j = start
                while j < len(code) and (code[j].isalnum() or code[j] in "._"):
                    j += 1
                end = j
            if end == start:
                pos = m.end()
                continue
            code = code[:m.start()] + "**(-" + code[start:end] + ")" + code[end:]
            pos = m.start() + 4 + (end - start) + 1
        out.append(code + sep + comment)
    return "\n".join(out)

_LOG_RE = re.compile(r'\blog(?!\w)\s*\(')

def _encode_log(src):
    """Rewrite base-10 log( to an internal name.

    handcalcs typesets log() as \\ln (Python's meaning). unitcalcs uses the engineering
    convention log = base 10, so the printed symbol must be \\log, not \\ln.
    """
    out = []
    for line in src.splitlines():
        code, sep, comment = line.partition('#')
        out.append(_LOG_RE.sub('LOGTENQQ(', code) + sep + comment)
    return "\n".join(out)

def _encode_primes(src):
    """Allow primed symbols such as R'_w,ges (DIN 4109 resultierendes Schalldaemm-Mass).

    Python reads the apostrophe as the start of a string literal, so it is swapped for a
    token and restored as a prime in the output.
    """
    out = []
    for line in src.splitlines():
        code, sep, comment = line.partition('#')
        out.append(code.replace("'", _PRIME_TOKEN) + sep + comment)
    return "\n".join(out)

# A comma is part of a symbol (R_w,ges / R_w,1 / L_n,w) when it sits TIGHT between
# identifier characters. A comma followed by a space separates function arguments
# (min(a, b)) and is left alone. So: write "min(a, b)" with a space, "R_w,ges" without.
_COMMA_SUB_RE = re.compile(r"(?<=[\w'])\s?,(?=[A-Za-z0-9_])")

def _encode_commas(src):
    """Turn 'R_w,ges' into a valid Python name so it is not read as tuple unpacking.

    Comma subscripts are standard German engineering notation, but Python parses the
    comma as unpacking -> 'cannot unpack non-iterable int object'.
    """
    out = []
    for line in src.splitlines():
        code, sep, comment = line.partition('#')
        out.append(_COMMA_SUB_RE.sub(_COMMA_TOKEN, code) + sep + comment)
    return "\n".join(out)

# Greek names that handcalcs does not turn into symbols when they PREFIX another
# symbol: it renders \mathrm{DeltaR'} instead of \Delta R'. Writing DeltaR'_w,Tr is the
# natural spelling for a difference of a quantity, so the prefix is converted here.
_GREEK = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
          "omicron pi rho sigma tau upsilon phi chi psi omega "
          "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu Nu Xi "
          "Omicron Pi Rho Sigma Tau Upsilon Phi Chi Psi Omega").split()
_GREEK_RE = re.compile(r"\\mathrm\{(" + "|".join(sorted(_GREEK, key=len, reverse=True))
                       + r")([A-Za-z0-9']*)\}")

def _decode_greek(text):
    r"""\mathrm{DeltaR'} -> \Delta R' ,  \mathrm{lambda} -> \lambda ."""
    def sub(m):
        name, rest = m.group(1), m.group(2)
        return "\\" + name + (" " + rest if rest else "")
    return _GREEK_RE.sub(sub, text)

def _decode_commas(text):
    text = text.replace(_COMMA_TOKEN, ",").replace(_PRIME_TOKEN, "'")
    text = text.replace(r'\operatorname{LOGTENQQ}', r'\log')
    text = _decode_greek(text)
    # a primed single letter comes back as \mathrm{R'} (upright); make it italic R'
    return re.sub(r"\\mathrm\{([A-Za-z])'\}", r"\1'", text)

_NUMUNIT_RE = re.compile(r'(?<=[\d\.])\s*([A-Za-z_\u00b5]\w*)')

def _check_units(src):
    """Fail with a readable message when a number is followed by an unknown unit."""
    unknown = []
    for line in src.splitlines():
        code = line.split('#')[0]
        for name in _NUMUNIT_RE.findall(code):
            if name not in UNIT_NS and name not in unknown:
                unknown.append(name)
    if unknown:
        known = ", ".join(sorted(UNIT_NS)[:18])
        raise ValueError(
            "unitcalcs: unknown unit(s) %s. Known units include: %s, ... "
            "Add missing ones in _extra_units() in unitcalcs_tex.py."
            % (", ".join(repr(x) for x in unknown), known))

def _preprocess(src):
    out = []
    for line in src.splitlines():
        line = re.sub(r'(?<=[\d\.])\s+(?=(?:'+_UNIT_RE+r')\b)', ' * ', line)
        line = re.sub(r'(\d)((?:'+_UNIT_RE+r')\b)', r'\1 * \2', line)
        out.append(line)
    return '\n'.join(out)

def _inner(block):
    m = re.search(r'\\begin\{aligned\}(.*)\\end\{aligned\}', block, re.S)
    return m.group(1).strip('\n') if m else block

def _dedent(src):
    """Strip leading/trailing whitespace per line and drop blank lines.

    Each calc line is a standalone assignment, so indentation carries no meaning.
    Users naturally indent inside \\begin{calc} (as in align), which would otherwise
    raise IndentationError when the block is exec'd.
    """
    return "\n".join(l.strip() for l in src.expandtabs(4).splitlines() if l.strip())

_ALIGN_RE = re.compile(r'^#\s*(left|right|center)\s*$', re.I)

def _split_align(src):
    """Pull an optional alignment directive (#left / #right / #center) off the top.

    Written inside the block because an optional argument on \\begin{calc} cannot be
    scanned without destroying the line break fancyvrb requires.
    """
    align, kept = "center", []
    for line in src.splitlines():
        m = _ALIGN_RE.match(line.strip())
        if m and not kept:
            align = m.group(1).lower()
            continue
        kept.append(line)
    return align, "\n".join(kept)

def render_aligned(src, precision=2):
    """Full output including the math wrapper chosen by the directive."""
    align, body = _split_align(src)
    inner = _render(body, precision)
    if align == "left":
        return "\\begin{flushleft}$\\displaystyle " + inner + " $\\end{flushleft}"
    if align == "right":
        return "\\begin{flushright}$\\displaystyle " + inner + " $\\end{flushright}"
    return "\\[\n" + inner + "\n\\]"

def _wrap(rows, align):
    """Wrap rendered rows in a PAGE-BREAKABLE math environment.

    'aligned' inside display math is a single unbreakable box, so a long block could
    only be pushed whole to the next page. align*/flalign* break between rows while
    \allowdisplaybreaks is active (unitcalcs.sty switches it on).

    A row separator may carry an optional spacing argument: some handcalcs versions end
    a row with "\\[10pt]". That argument is captured together with the separator and
    re-emitted. Splitting on "\\" alone would strand "[10pt]" at the start of the next
    row, where LaTeX typesets it as literal text.
    """
    parts = re.split(r"\\\\(\[[^\]]*\])?", rows)
    items = []                      # (row text, spacing that followed the break)
    i = 0
    while i < len(parts):
        text = (parts[i] or "").strip()
        gap = parts[i + 1] if i + 1 < len(parts) else None
        if text:
            items.append((text, gap or ""))
        i += 2
    if not items:
        return ""
    if align in ("left", "right"):
        pre, post = ("", " &&") if align == "left" else ("&& ", "")
        lines = [pre + t + post + r"\\" + g for t, g in items[:-1]]
        lines.append(pre + items[-1][0] + post)
        return "\\begin{flalign*}\n" + "\n".join(lines) + "\n\\end{flalign*}"
    lines = [t + " " + r"\\" + g for t, g in items[:-1]]
    lines.append(items[-1][0])
    return "\\begin{align*}\n" + "\n".join(lines) + "\n\\end{align*}"

def render_center(src, precision=2):
    return _wrap(_render(src, precision), "center")

def render_left(src, precision=2):
    return _wrap(_render(src, precision), "left")

def render_right(src, precision=2):
    return _wrap(_render(src, precision), "right")

def render_body(src, precision=2):
    """Render the calc block WITHOUT math delimiters (an aligned environment only).

    unitcalcs.sty wraps this itself so the [left]/[right]/[center] option can be
    handled purely in LaTeX.
    """
    return "\\begin{aligned}\n" + _render(src, precision) + "\n\\end{aligned}"

def render_calc(src, precision=2):
    """Render the calc block wrapped in display math (for direct \\input use)."""
    return _wrap(_render(src, precision), "center")

# --- language ----------------------------------------------------------------
# Selected by the package option: \usepackage[german]{unitcalcs} or [english].
# Affects the decimal separator and the wording of a fulfilled/failed check.
# Comma subscripts (R_w,ges) work in every language.
LANGUAGE = "english"

# Verdict wording for a bare comparison line. Edit here to change it globally.
VERDICTS = {
    "german":  (r"\textrm{erf\"ullt}", r"\textrm{nicht erf\"ullt}"),
    "english": (r"\textrm{checked}",   r"\textrm{not checked}"),
}

def setlanguagegerman():
    """Decimal comma, verdicts 'erfuellt' / 'nicht erfuellt'."""
    global LANGUAGE
    LANGUAGE = "german"
    return ""

def setlanguageenglish():
    """Decimal point, verdicts 'checked' / 'not checked'."""
    global LANGUAGE
    LANGUAGE = "english"
    return ""

_DEC_RE = re.compile(r"(\d)\.(\d)")
_TEXTRM_RE = re.compile(r"\\textrm\{[^{}]*\}")

def _decimal_separator(text):
    """German: 1.35 -> 1{,}35 in maths, leaving comment text untouched.

    {,} is used rather than a bare comma so TeX does not add list spacing after it.
    Comments are rendered inside \\textrm{...}; those spans are skipped so that e.g.
    'DIN 4109-2 Tab. 1' keeps its full stops.
    """
    if LANGUAGE != "german":
        return text
    out, i = [], 0
    for m in _TEXTRM_RE.finditer(text):
        out.append(_DEC_RE.sub(r"\1{,}\2", text[i:m.start()]))
        out.append(m.group(0))
        i = m.end()
    out.append(_DEC_RE.sub(r"\1{,}\2", text[i:]))
    return "".join(out)

# --- comparison / Nachweis support -------------------------------------------
# Verdict wording for a bare comparison line. Change these two if you prefer
# "OK"/"nicht OK" or English wording.
# Unicode a keyboard or a norm PDF produces, mapped to what Python understands.
_UNICODE_OPS = {
    "\u2264": "<=", "\u2265": ">=", "\u2260": "!=",      # <= >= !=
    "\u00b7": "*", "\u00d7": "*", "\u2212": "-",          # middle dot, times, minus
    "\u00b2": "**2", "\u00b3": "**3",                     # squared, cubed
}

def _encode_unicode_ops(src):
    """Accept the symbols actually typed in a German office: <=, >=, !=, *, -, squares."""
    out = []
    for line in src.splitlines():
        code, sep, comment = line.partition("#")
        for uni, ascii_ in _UNICODE_OPS.items():
            code = code.replace(uni, ascii_)
        out.append(code + sep + comment)
    return "\n".join(out)

# an assignment '=' is one that is not part of ==, <=, >=, !=
_ASSIGN_RE = re.compile(r"(?<![<>=!])=(?!=)")
_CMP_RE = re.compile(r"(<=|>=|==|!=|<|>)")

def _split_assign(code):
    """Return (lhs, rhs) for an assignment line, or None for anything else."""
    m = _ASSIGN_RE.search(code)
    if not m:
        return None
    return code[:m.start()], code[m.end():]

_OP_TEX = {">=": r"\geq", "<=": r"\leq", ">": r"\gt", "<": r"\lt",
           "==": "=", "!=": r"\neq"}
_IDENT_RE = re.compile(r"^[A-Za-z_]\w*$")

def _render_requirement(line, lhs, op, rhs, precision):
    """A comparison whose left side is a NEW name states a requirement, not a check.

        R_w,erf >= 53      ->  defines R_w,erf = 53, printed as  R_w,erf >= 53

    The value is stored so later lines (R_w,vorh >= R_w,erf) can use it.
    """
    code, sep, comment = line.partition("#")
    exec(f"{lhs} = {rhs}", _SESSION)
    _USER_VARS.add(lhs)
    rendered = _inner(hc.LatexRenderer(
        f"{lhs} = {rhs}" + (sep + comment if comment.strip() else ""),
        _SESSION, {"override": "params", "precision": precision, "sci_not": None}).render())
    # swap the assignment sign for the requirement sign
    return rendered.replace("&=", "&" + _OP_TEX.get(op, "="), 1)

def _render_comparison(line, precision):
    """Render a bare comparison (a Nachweis row) as: symbolic => values => verdict."""
    code, sep, comment = line.partition("#")
    tmp = "unitcalcscheck"
    rendered = _inner(hc.LatexRenderer(
        f"{tmp} = {code.strip()}", _SESSION,
        {"override": "long", "precision": precision, "sci_not": None}).render())
    # rendered looks like:  \mathrm{unitcalcscheck} &= SYMBOLIC \\&= SUBSTITUTED \\&= True ...
    parts = rendered.split(r"\\&=")
    if len(parts) < 3:
        return rendered
    symbolic = parts[0].split("&=", 1)[-1].strip()
    substituted = parts[1].strip()
    ok, not_ok = VERDICTS[LANGUAGE]
    verdict = ok if _SESSION.get(tmp) else not_ok
    note = ""
    if comment.strip():
        note = r" \; \;\textrm{(" + comment.strip() + ")}"
    arrow = r" \;\Rightarrow\; "
    return symbolic + " &" + arrow.join(["", substituted, verdict]).lstrip() + note

def _render(src, precision=2):
    raw = _encode_unicode_ops(_dedent(src))   # translate unicode FIRST, so the unit
                                              # check sees m**2 rather than 'm\u00b2'
    _check_units(raw)          # on text with commas/primes still intact: encoded names
                               # contain digits (R_w,1 -> R_wQQCQQ1) and would otherwise
                               # look like unknown units
    src = _preprocess(_fix_pow_minus(_encode_commas(_encode_log(_encode_primes(raw)))))
    bodies = []
    for line in src.splitlines():
        code = line.split('#')[0]
        if not code.strip():
            continue
        parts = _split_assign(code)
        if parts is None:
            # no assignment: a bare comparison is a Nachweis row (R_vorh >= R_erf)
            m = _CMP_RE.search(code)
            if m:
                lhs = code[:m.start()].strip()
                rhs = code[m.end():].strip()
                # Decide by the RIGHT side, not by whether the name is known:
                #   name >= literal   -> REQUIREMENT (defines/updates the value)
                #   name >= variable  -> NACHWEIS   (compares two quantities)
                # Deciding by "is the name known" was unsafe: a second requirement for
                # the same symbol (R'_w,erf >= 53 then >= 56, two norms) turned into a
                # check and silently kept the first value.
                rhs_ids = set(re.findall(r'[A-Za-z_]\w*', rhs))
                if _IDENT_RE.match(lhs) and not (rhs_ids & _USER_VARS):
                    bodies.append(_render_requirement(line, lhs, m.group(1), rhs, precision))
                else:
                    exec("unitcalcscheck = " + code.strip(), _SESSION)
                    bodies.append(_render_comparison(line, precision))
            continue
        # Execute and render line by line, NOT the whole block first: handcalcs reads
        # values out of the namespace at render time, so a symbol assigned twice in one
        # block (R'_w = 53 then R'_w = 56) would otherwise print the final value on both
        # lines. Rendering immediately after each line shows the value it had there.
        exec(line, _SESSION)
        lhs, rhs = parts
        ids = set(re.findall(r'[A-Za-z_]\w*', rhs))
        kind = 'long' if (ids & _USER_VARS) else 'params'   # refs a prior var -> worked
        _USER_VARS.add(lhs.strip())
        la = {"override": kind, "precision": precision, "sci_not": None}
        bodies.append(_inner(hc.LatexRenderer(line, _SESSION, la).render()))
    return _decimal_separator(_decode_commas(" \\\\\n".join(bodies)))

def val(name, unit_str=None):
    name = re.sub(r'\s*,\s*', _COMMA_TOKEN, name).replace("'", _PRIME_TOKEN)
    """Return a stored value as a plain number (optionally in a given unit) for export."""
    q = _SESSION[name]
    return q


# --- PythonTeX inline support -------------------------------------------------
# Each \begin{calc} block writes its body (verbatim) to calcblock<N>.tmp on the
# LaTeX side. Python keeps its OWN counter, so the \py{} call carries no LaTeX
# macros (that was the FileNotFoundError bug). reset() zeroes it per run.
_BLOCK_I = 0
_PYTEX = None

def set_pytex(p):
    """Receive PythonTeX's pytex object and register THIS module as a dependency.

    PythonTeX re-executes a \\py{} call only when the code string changes. Since the
    call is always the identical 'emitcalc()', editing this engine would otherwise be
    ignored and stale cached output reused. Registering the module file makes
    PythonTeX notice when the engine changes.
    """
    global _PYTEX
    _PYTEX = p
    try:
        p.add_dependencies(os.path.abspath(__file__))
    except Exception:
        pass

def _reset_blocks():
    global _BLOCK_I
    _BLOCK_I = 0

def _jobname():
    """Discover the document jobname from PythonTeX's output dir (pythontex-files-<jobname>)."""
    import inspect
    try:
        for fr in inspect.stack():
            f = fr.frame.f_globals.get("__file__")
            if f and "pythontex-files-" in f:
                d = os.path.basename(os.path.dirname(os.path.abspath(f)))
                return d.split("pythontex-files-", 1)[1]
    except Exception:
        pass
    return ""

def _block_file(n):
    """Locate the Nth block file written by LaTeX for this document."""
    job = _jobname()
    candidates = []
    if job:
        candidates.append(f"{job}-calcblock{n}.tmp")
    candidates.append(f"calcblock{n}.tmp")
    hits = glob.glob(f"*-calcblock{n}.tmp")
    if len(hits) == 1:
        candidates.append(hits[0])
    for fname in candidates:
        if os.path.exists(fname):
            return fname
    raise FileNotFoundError(
        f"calc block {n}: none of {candidates} found in {os.getcwd()}. "
        "Run pdflatex before pythontex, and don't interleave two documents.")

def _emit(align, precision=2):
    """Read the next block written by LaTeX and render it with the given alignment."""
    global _BLOCK_I
    fname = _block_file(_BLOCK_I)
    _BLOCK_I += 1
    try:
        if _PYTEX is not None:
            _PYTEX.add_dependencies(os.path.abspath(fname))
    except Exception:
        pass
    with open(fname, encoding="utf-8") as f:
        return _wrap(_render(f.read(), precision), align)

def emit_calc(precision=2):
    return _emit("center", precision)

# --- underscore-free aliases -------------------------------------------------
# \py{} inside a \newenvironment body is tokenized at DEFINITION time, where '_'
# still has catcode 8 (subscript) and gets mangled. These aliases avoid '_' so the
# calc environment in unitcalcs.sty can call them safely.
emitcalc = emit_calc

def emitcenter(precision=2):
    return _emit("center", precision)

def emitleft(precision=2):
    return _emit("left", precision)

def emitright(precision=2):
    return _emit("right", precision)
rendercalc = render_calc
renderbody = render_body
renderaligned = render_aligned
setpytex = set_pytex

# --- installing the style file after a plain pip install ----------------------
def _find_sty():
    """Locate unitcalcs.sty: shipped with the wheel, or next to this module."""
    import sys, sysconfig
    candidates = [
        os.path.join(sys.prefix, "share", "unitcalcs", "unitcalcs.sty"),
        os.path.join(sysconfig.get_paths().get("data", sys.prefix),
                     "share", "unitcalcs", "unitcalcs.sty"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "unitcalcs.sty"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "unitcalcs.sty not found. Looked in:\n  " + "\n  ".join(candidates))

def install_sty_cli():
    """Copy unitcalcs.sty into the personal TeX tree (TEXMFHOME).

    pip cannot install a LaTeX style file, so this console script does it:

        unitcalcs-install-sty
    """
    import shutil, subprocess
    src = _find_sty()
    home = subprocess.run(["kpsewhich", "-var-value", "TEXMFHOME"],
                          capture_output=True, text=True).stdout.strip()
    if not home:
        raise SystemExit("kpsewhich not found - is a TeX distribution installed?")
    dest_dir = os.path.join(home, "tex", "latex", "unitcalcs")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "unitcalcs.sty"))
    subprocess.run(["mktexlsr", home], capture_output=True)
    found = subprocess.run(["kpsewhich", "unitcalcs.sty"],
                           capture_output=True, text=True, cwd="/").stdout.strip()
    print(f"installed: {os.path.join(dest_dir, 'unitcalcs.sty')}")
    print(f"kpsewhich: {found or 'NOT FOUND - check your TeX installation'}")
