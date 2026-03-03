#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

usage() {
  echo "Usage: $0 <file> <name> <version> <model_type> <dataset> <owner> [params_json] [feature_names_json] [git_path]"
  echo ""
  echo "Example:"
  echo "  $0 ./model.bin my_model 1.0.0 catboost dataset_v1 alice '{\"lr\":0.1}' '[\"f1\",\"f2\"]' 'https://git/repo'"
}

if [ "$#" -lt 6 ]; then
  usage
  exit 1
fi

FILE_PATH="$1"
NAME="$2"
VERSION="$3"
MODEL_TYPE="$4"
DATASET="$5"
OWNER="$6"
PARAMS_JSON="${7:-}"
FEATURE_NAMES_JSON="${8:-}"
GIT_PATH="${9:-}"

if [ ! -f "$FILE_PATH" ]; then
  echo "File not found: $FILE_PATH"
  exit 1
fi

curl -sS -X POST "${API_URL}/models" \
  -F "name=${NAME}" \
  -F "version=${VERSION}" \
  -F "model_type=${MODEL_TYPE}" \
  -F "dataset=${DATASET}" \
  -F "owner=${OWNER}" \
  ${PARAMS_JSON:+-F "params=${PARAMS_JSON}"} \
  ${FEATURE_NAMES_JSON:+-F "feature_names=${FEATURE_NAMES_JSON}"} \
  ${GIT_PATH:+-F "git_path=${GIT_PATH}"} \
  -F "file=@${FILE_PATH}"
