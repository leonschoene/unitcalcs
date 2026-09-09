#!/bin/sh
# clean.sh -- remove unitcalcs/PythonTeX build artefacts after the PDF is finished.
#   ./clean.sh            artefacts for every document in this folder
#   ./clean.sh example    artefacts for one document
#   ./clean.sh -a         also remove .aux .log .out .synctex.gz
# NOTE: removing pythontex-files-<job> deletes the cached results, so the NEXT build
# must run the full chain (pdflatex -> pythontex -> pdflatex).
ALL=0; [ "$1" = "-a" ] && { ALL=1; shift; }
JOB="$1"
if [ -n "$JOB" ]; then
  rm -f "$JOB"-calcblock*.tmp "$JOB".pytxcode
  rm -rf "pythontex-files-$JOB"
  [ "$ALL" = 1 ] && rm -f "$JOB".aux "$JOB".log "$JOB".out "$JOB".synctex.gz
else
  rm -f ./*-calcblock*.tmp ./*.pytxcode
  rm -rf ./pythontex-files-*
  [ "$ALL" = 1 ] && rm -f ./*.aux ./*.log ./*.out ./*.synctex.gz
fi
rm -rf ./__pycache__
echo "cleaned${JOB:+ ($JOB)}"
