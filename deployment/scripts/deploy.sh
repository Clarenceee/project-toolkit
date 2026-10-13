#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/deploy.sh <environment>" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app_file="${script_dir}/../apps/${1}-applications.yaml"

if [[ ! -f "${app_file}" ]]; then
  echo "Missing App-of-Apps file: ${app_file}" >&2
  exit 2
fi

kubectl apply -f "${app_file}"
