#!/usr/bin/env bash
# Lab 4 — 같은 과제를 하네스별로 헤드리스 실행. 사용법은 run_task.py --help
#   ./lab4_public_harness/run_task.sh bare
#   ./lab4_public_harness/run_task.sh mine
#   ./lab4_public_harness/run_task.sh superpowers            (설치된 플러그인 사용)
#   ./lab4_public_harness/run_task.sh superpowers --plugin-dir ~/src/superpowers
#   ./lab4_public_harness/run_task.sh gstack --dry-run
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" lab4_public_harness/run_task.py "$@"
