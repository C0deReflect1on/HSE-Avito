#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCHMARK_DIR="${ROOT_DIR}/benchmark"

CONTAINER_NAME="${CONTAINER_NAME:-embeddings-service}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PORT="${PORT:-8000}"
RUNS="${RUNS:-5}"
MAX_BATCH_SIZE="${MAX_BATCH_SIZE:-32}"
BATCH_WINDOW_MS="${BATCH_WINDOW_MS:-500}"
SKIP_SUSTAINED="${SKIP_SUSTAINED:-0}"
HF_IMAGE="${HF_IMAGE:-embeddings-service:hf}"
ONNX_IMAGE="${ONNX_IMAGE:-embeddings-service:onnx}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_benchmark_deps() {
  if python3 -c "import httpx, numpy" >/dev/null 2>&1; then
    return 0
  fi

  echo "==> Installing benchmark Python dependencies"
  python3 -m pip install -r "${BENCHMARK_DIR}/requirements.txt"
}

cleanup_container() {
  if docker ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
}

wait_for_health() {
  local attempt
  for attempt in $(seq 1 60); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "Service did not become healthy at ${BASE_URL}" >&2
  return 1
}

build_image() {
  local backend="$1"
  local image="$2"
  echo "==> Building ${backend} image: ${image}"
  docker build \
    --build-arg INFERENCE_BACKEND="${backend}" \
    -t "${image}" \
    "${ROOT_DIR}"
}

run_case() {
  local backend="$1"
  local batching_enabled="$2"
  local image="$3"
  local run_name="$4"

  cleanup_container

  echo "==> Starting ${run_name}"
  docker run --rm -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8000" \
    -e INFERENCE_BACKEND="${backend}" \
    -e BATCHING_ENABLED="${batching_enabled}" \
    -e MAX_BATCH_SIZE="${MAX_BATCH_SIZE}" \
    -e BATCH_WINDOW_MS="${BATCH_WINDOW_MS}" \
    "${image}" >/dev/null

  wait_for_health

  local extra_args=()
  if [[ "${SKIP_SUSTAINED}" == "1" ]]; then
    extra_args+=(--skip-sustained)
  fi

  (
    cd "${ROOT_DIR}"
    local cmd=(
      python3 benchmark/run_benchmark.py
      --base-url "${BASE_URL}"
      --container "${CONTAINER_NAME}"
      --run-name "${run_name}"
      --runs "${RUNS}"
    )
    if [[ ${#extra_args[@]} -gt 0 ]]; then
      cmd+=("${extra_args[@]}")
    fi
    "${cmd[@]}"
  )

  cleanup_container
}

main() {
  require_cmd docker
  require_cmd curl
  require_cmd python3
  ensure_benchmark_deps

  cleanup_container
  trap cleanup_container EXIT

  build_image hf "${HF_IMAGE}"
  build_image onnx "${ONNX_IMAGE}"

  run_case hf false "${HF_IMAGE}" "hf_no_batch"
  run_case hf true "${HF_IMAGE}" "hf_batch_bw${BATCH_WINDOW_MS}"
  run_case onnx false "${ONNX_IMAGE}" "onnx_no_batch"
  run_case onnx true "${ONNX_IMAGE}" "onnx_batch_bw${BATCH_WINDOW_MS}"

  echo "==> Done"
  echo "Results saved under ${BENCHMARK_DIR}/results/"
}

main "$@"
