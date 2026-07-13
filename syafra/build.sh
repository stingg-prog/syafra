#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Build Tailwind CSS from source
npm ci --omit=dev 2>/dev/null || npm install
npm run build:css:minify

python manage.py collectstatic --noinput
