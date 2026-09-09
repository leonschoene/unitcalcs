#!/bin/sh
# install.sh -- install unitcalcs so \usepackage{unitcalcs} works in ANY folder.
#
#   ./install.sh              editable install (recommended while you still tweak the engine)
#   ./install.sh --copy       plain install (a fixed copy; re-run install.sh after edits)
#
# Installs two halves:
#   1. unitcalcs.sty  -> your personal TeX tree (TEXMFHOME), found by kpsewhich
#   2. unitcalcs_tex  -> your Python environment, importable by PythonTeX
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

# --- 1. Python side -----------------------------------------------------------
PYBIN=${PYTHON:-python3}
echo "Python: $($PYBIN -c 'import sys; print(sys.executable)')"
if [ "$1" = "--copy" ]; then
    "$PYBIN" -m pip install "$HERE"
else
    "$PYBIN" -m pip install -e "$HERE"
fi

# --- 2. LaTeX side ------------------------------------------------------------
TEXMFHOME=$(kpsewhich -var-value TEXMFHOME)
DEST="$TEXMFHOME/tex/latex/unitcalcs"
mkdir -p "$DEST"
cp "$HERE/unitcalcs.sty" "$DEST/"
echo "unitcalcs.sty -> $DEST"
mktexlsr "$TEXMFHOME" >/dev/null 2>&1 || true

# --- 3. Check -----------------------------------------------------------------
echo
echo "kpsewhich unitcalcs.sty : $(cd / && kpsewhich unitcalcs.sty || echo 'NOT FOUND')"
echo "python import           : $(cd / && "$PYBIN" -c 'import unitcalcs_tex; print(unitcalcs_tex.__file__)' 2>&1)"
echo
echo "Done. In any document:  \\usepackage{unitcalcs}"
echo "Build as usual:         pdflatex -> pythontex -> pdflatex"
