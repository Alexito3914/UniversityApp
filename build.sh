#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_demo
if [ -f data/HORARIOS_25_26.xlsx ]; then
  python manage.py import_horarios_excel --year 2026-2027 --clear-eps --apply-schedule
fi
