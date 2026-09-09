# unitcalcs

Unit-aware, Mathcad/Calcpad-style worked calculations inside a LaTeX document.

You write plain assignment lines; unitcalcs renders them as a worked calculation —
symbolic formula, then the same formula with the values substituted, then the result —
with units carried through the arithmetic automatically:

```latex
\begin{calc}[left]
    gamma_G = 1.35      # partial safety factor
    G_k = 32 kN/m       # characteristic load
    N_Ed = gamma_G*G_k  # design value
\end{calc}
```

renders as

> N_Ed = γ_G · G_k = 1.35 · 32.00 kN/m = 43.20 kN/m  (design value)

Values persist across blocks, so a quantity defined in an early chapter can be used in a
later one. Under the hood the calculation is executed by
[handcalcs](https://github.com/connorferster/handcalcs) and
[forallpeople](https://github.com/connorferster/forallpeople), driven from LaTeX by
[PythonTeX](https://github.com/gpoore/pythontex).

---

## 1. Installation

### Prerequisites

| Requirement | Notes |
|---|---|
| TeX distribution | TeX Live / MacTeX. Needs `pythontex`, `fancyvrb`, `amsmath` (full MacTeX has all three; with BasicTeX run `sudo tlmgr install pythontex`) |
| Python | 3.8 or newer |

`handcalcs` and `forallpeople` are installed automatically by the steps below.

**Important:** install into the *same* Python that PythonTeX calls. If you use Anaconda,
prefix the install commands with that interpreter (see the note after each method).
`which python3` prints the path you are currently using.

### Method A — from a downloaded folder

Assuming the folder sits in your `Downloads` directory:

```sh
cd ~/Downloads/unitcalcs
chmod +x install.sh
./install.sh
```

With Anaconda (or any non-default interpreter):

```sh
PYTHON=/opt/anaconda3/bin/python3 ./install.sh
```

### Method B — from GitHub

```sh
git clone https://github.com/leonschoene/unitcalcs.git
cd unitcalcs
chmod +x install.sh
./install.sh
```

Or, without cloning, install the Python half directly and copy the style file
afterwards:

```sh
pip install git+https://github.com/leonschoene/unitcalcs.git
```

### What the installer does

It installs the two halves of the package into the two places they belong:

1. `unitcalcs.sty` is copied to your personal TeX tree,
   `$(kpsewhich -var-value TEXMFHOME)/tex/latex/unitcalcs/`. This location survives TeX
   Live updates and is found by `kpsewhich` from any directory.
2. `unitcalcs_tex.py` is installed into your Python environment with `pip install -e .`
   (an *editable* install, so edits to the engine take effect immediately). Use
   `./install.sh --copy` for a fixed copy instead.

Manual equivalent, if you prefer to do it yourself:

```sh
pip install -e .
mkdir -p "$(kpsewhich -var-value TEXMFHOME)/tex/latex/unitcalcs"
cp unitcalcs.sty "$(kpsewhich -var-value TEXMFHOME)/tex/latex/unitcalcs/"
mktexlsr "$(kpsewhich -var-value TEXMFHOME)"
```

### Verifying the installation

```sh
kpsewhich unitcalcs.sty                                   # prints a path
python3 -c "import unitcalcs_tex; print(unitcalcs_tex.__file__)"
python3 check_unitcalcs.py                                # checks every dependency
```

After installation, any document in any folder needs only `\usepackage{unitcalcs}` — no
files have to be copied into the project directory.

---

## 2. Building a document

unitcalcs runs Python during the LaTeX build, so a document needs three passes:

```sh
pdflatex example
pythontex example
pdflatex example
```

If the calculations show as `??`, PythonTeX has not run since the last `pdflatex`.

### TeXstudio

TeXstudio's default build runs only `pdflatex`, so the calculations would never be
executed. Add PythonTeX as a user command and chain it:

1. Preferences (`⌘,`) → tick **Show Advanced Options** (bottom left) → **Build**.
2. Under *User Commands*, add `user0:PythonTeX` with the command `pythontex "%"`.
3. Set *Build & View* to
   `txs:///pdflatex | txs:///user0 | txs:///pdflatex | txs:///view-pdf`.

If PythonTeX is not found, or runs the wrong Python, give both paths explicitly:

```
env PYTHONWARNINGS=ignore::SyntaxWarning /opt/anaconda3/bin/python3 \
    /usr/local/texlive/2025/texmf-dist/scripts/pythontex/pythontex3.py \
    --interpreter python:/opt/anaconda3/bin/python3 %
```

`PYTHONWARNINGS=ignore::SyntaxWarning` suppresses the `invalid escape sequence` messages
that PythonTeX 0.18 produces on Python 3.12; they are harmless.

---

## 3. Language option

```latex
\usepackage[english]{unitcalcs}   % default
\usepackage[german]{unitcalcs}
```

| | `english` | `german` |
|---|---|---|
| Decimal separator | `1.35` | `1,35` |
| Fulfilled check | `checked` | `erfüllt` |
| Failed check | `not checked` | `nicht erfüllt` |

The decimal separator applies to the mathematics only; text in comments is left alone,
so `# DIN 4109-2 Tab. 1` keeps its full stops. Comma subscripts (`R_w,ges`) work in
every language. To change the wording, edit `VERDICTS` at the top of `unitcalcs_tex.py`.

---

## 4. Writing calculations

### The `calc` environment

```latex
\begin{calc}          ... \end{calc}   % centred (default)
\begin{calc}[left]    ... \end{calc}
\begin{calc}[right]   ... \end{calc}
\begin{calc}[center]  ... \end{calc}
```

One assignment per line; `# text` after a line becomes the annotation printed in
parentheses. Indentation is ignored, so blocks can be indented like any other LaTeX
environment.

Lines built only from literals are printed as plain values; lines that reference an
earlier variable are printed in the full worked form. To see the substitution steps,
assign the inputs to names first.

### Printing a stored value inline

```latex
The design value is $N_{Ed} = \py{str(val('N_Ed'))}$.
```

Call `\py` directly — wrapping it in `\newcommand` does not work, because PythonTeX
reads its argument verbatim.

### Units

Unit names come from forallpeople's `structural` environment: `m`, `mm`, `kN`, `N`,
`MPa`, `kPa`, `GPa`, `Pa`, `kg`, `s`, `J`, `W`, and the imperial set `ft`, `inch`,
`kip`, `psi`, `ksi`, `psf`, `pcf`. unitcalcs adds `cm`, `dm`, `km`, `um`, `g`, `t`,
`kNm`, `MNm`, `Ncm`, `kJ`, `kW`, `MW`, `hPa`, `bar`, `N_mm2`, `h`, `Hz`, `kHz`.

```
d = 24 cm           # a space is optional: 24cm works too
A = 12 m**2         # or 12 m² — the superscript is translated
p = 5 kN/m**2
```

A number followed by an unknown name raises a readable error naming the unit. Add
missing units to `_extra_units()` in `unitcalcs_tex.py`. Note that forallpeople
normalises the display, so `3 cm` prints as `30.00 mm`.

`min` is the function `min(a, b)`, not minutes.

### Symbols

| You write | Renders as | Notes |
|---|---|---|
| `sigma_c` | σ_c | Greek name as the base symbol |
| `DeltaR_w` | ΔR_w | Greek name prefixed to another symbol |
| `R_w,ges` | R_{w,ges} | comma subscript |
| `R_w,1` | R_{w,1} | numeric subscript |
| `R'_w` | R′_w | prime |

Greek is written by name (`alpha`, `sigma`, `Delta`, `psi`, `lambda`, …), never as
LaTeX: a calc line is Python, so `$\Delta$` cannot work.

A comma tight between characters belongs to the symbol; a comma followed by a space
separates function arguments:

```
R_w,ges = 53        # symbol
c = min(a, b)       # arguments — note the space
```

### Mathematics

```
log, log10, lg   base 10        ln, log_e   natural        log2, ld, lb   base 2
exp, sqrt, sin, cos, tan, asin, acos, atan, atan2, sinh, cosh, tanh
radians, degrees, floor, ceil, abs, min, max, round, sum, pi, e
```

`log` is **base 10**, following the engineering convention in both English and German
texts. This differs from Python, where `math.log` is natural. Each spelling prints its
own symbol, so the document can match its source: `log` → log, `lg` → lg, `log10` →
log₁₀.

The Unicode symbols `≤ ≥ ≠ · × −` and the superscripts `² ³` are accepted and
translated.

### Requirements and verifications

The right-hand side decides what a comparison means:

```
name >= NUMBER      # requirement: defines/updates the value, prints the sign
name >= VARIABLE    # verification: compares the two, prints the verdict
```

```
R_w,req >= 53          # requirement (stores 53)
R_w,req >= 56          # a second requirement, e.g. from another standard (updates to 56)
R_w,vorh = 58
R_w,vorh >= R_w,req    # verification: 58 >= 56 => checked
```

So a verification always compares two named quantities; name the limit first, then check
against it. Naming the check also works and uses handcalcs' own form, ending in
`True`/`False`:

```
chk = R_w,vorh > R_w,req
```

### Page breaks

Blocks are emitted as `align*` (centred) or `flalign*` (left/right) with
`\allowdisplaybreaks`, so a long block splits across pages instead of being pushed whole
to the next one. To keep lines together, put them in their own `calc` block.

---

## 5. Build artefacts

A build creates `<job>-calcblock<N>.tmp` (block bodies), `<job>.pytxcode` (the list of
`\py` calls), `pythontex-files-<job>/` (generated script, cache and rendered results)
and `__pycache__/`. All are needed *during* the build; none are needed once the PDF
exists, so they can be deleted when the work is finished:

```sh
./clean.sh example      # artefacts for one document
./clean.sh              # every document in the folder
./clean.sh -a example   # also .aux .log .out .synctex.gz
```

Deleting `pythontex-files-<job>/` removes the cached results, so the next build must run
the full three-pass chain.

For an archive copy with no PythonTeX dependency, run `depythontex example`: it writes a
plain `.tex` with all results substituted, compilable with bare `pdflatex`.

---

## 6. Troubleshooting

| Symptom | Cause |
|---|---|
| `??` instead of calculations | PythonTeX has not run since the last `pdflatex` |
| `env: python: No such file or directory` | PythonTeX cannot find an interpreter named `python`; give the full path (see TeXstudio above) |
| `ModuleNotFoundError: unitcalcs_tex` | installed into a different Python than PythonTeX uses |
| Stale results after editing the engine | delete `pythontex-files-<job>/`, or add `--rerun=always` to the PythonTeX command |
| A verification prints as a plain requirement | the name on the left is misspelled, so it is treated as a new value |
| `unknown unit(s) '…'` | add the unit to `_extra_units()` |

---

## 7. Licence

unitcalcs is distributed under the [LaTeX Project Public License
1.3c](https://www.latex-project.org/lppl.txt) or later — the standard licence for LaTeX
packages, and the one CTAN expects. See [`LICENSE`](LICENSE) for the full notice.

It imports, but does not redistribute, handcalcs and forallpeople (Apache 2.0) and
PythonTeX, fancyvrb and amsmath (LPPL); these are installed separately by pip and by
your TeX distribution.
