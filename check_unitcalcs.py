#!/usr/bin/env python3
"""Verify every dependency unitcalcs needs (Python side + LaTeX side).

    python3 check_unitcalcs.py
"""
import importlib, shutil, subprocess, sys, os

OK, BAD = "\u2713", "\u2717"
problems = []

def line(ok, label, detail="", fix=""):
    print(f"  {OK if ok else BAD} {label:<28} {detail}")
    if not ok and fix:
        problems.append(fix)

def kpse(name):
    exe = shutil.which("kpsewhich")
    if not exe:
        return None
    try:
        return subprocess.run([exe, name], capture_output=True, text=True,
                              timeout=20).stdout.strip() or ""
    except Exception:
        return ""

print("\nPython side")
line(sys.version_info >= (3, 8), "Python >= 3.8", sys.version.split()[0])
for pkg in ("handcalcs", "forallpeople"):
    try:
        m = importlib.import_module(pkg)
        line(True, pkg, "v" + getattr(m, "__version__", "?"))
    except Exception as e:
        line(False, pkg, str(e), f"pip install {pkg}")
try:
    import forallpeople as u, handcalcs.handcalcs as hc
    u.environment("structural")
    ns = {"kN": u.kN, "m": u.m}
    exec("G_k = 32*kN/m\nN = 1.35*G_k", ns)
    tex = hc.LatexRenderer("N = 1.35*G_k", ns,
                           {"override": "long", "precision": 2, "sci_not": None}).render()
    line("kN/m" in tex and "43.20" in tex, "engine smoke test", "units + rendering work")
except Exception as e:
    line(False, "engine smoke test", str(e), "reinstall handcalcs + forallpeople")
try:
    sys.path.insert(0, os.getcwd())
    import unitcalcs_tex  # noqa
    line(True, "unitcalcs_tex", unitcalcs_tex.__file__)
except Exception as e:
    line(False, "unitcalcs_tex", str(e), "run ./install.sh")

print("\nLaTeX side")
if shutil.which("kpsewhich") is None:
    line(False, "TeX distribution", "kpsewhich not found",
         "install TeX Live / MacTeX and put it on PATH")
else:
    engine = next((e for e in ("pdflatex", "lualatex", "xelatex") if shutil.which(e)), None)
    line(bool(engine), "LaTeX engine", engine or "none found", "install TeX Live / MacTeX")
    for sty in ("pythontex.sty", "fancyvrb.sty", "amsmath.sty"):
        p = kpse(sty)
        line(bool(p), sty, p or "not found", f"tlmgr install {sty[:-4]}")
    line(bool(shutil.which("pythontex")), "pythontex (runner)",
         shutil.which("pythontex") or "not on PATH", "tlmgr install pythontex")
    p = kpse("unitcalcs.sty")
    line(bool(p), "unitcalcs.sty", p or "not found", "run ./install.sh")

print("\nSummary")
if problems:
    print(f"  {BAD} {len(problems)} item(s) need attention:")
    for f in dict.fromkeys(problems):
        print("     " + f)
    sys.exit(1)
print(f"  {OK} All dependencies present. Build: pdflatex -> pythontex -> pdflatex")
