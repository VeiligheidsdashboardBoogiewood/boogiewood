#!/usr/bin/env bash
# Bouwt de app opnieuw met bijgewerkte datasets en zet hem online.
# Gebruik: BW_BEHEER=<beheersleutel> tools/sync.sh [--peildatum] --set id=bestand.json [--set ...]
set -euo pipefail
cd "$(dirname "$0")/.."
git pull -q --rebase origin main || true
python3 -I tools/build.py --code 1082 --beheer "$BW_BEHEER" "$@"
git add -A
git -c user.name="Dashboard update" -c user.email="joeytwigt@gmail.com" commit -qm "Data bijgewerkt $(TZ=Europe/Amsterdam date '+%Y-%m-%d %H:%M')" || { echo "geen wijzigingen"; exit 0; }
git push -q origin main
echo "app bijgewerkt"
