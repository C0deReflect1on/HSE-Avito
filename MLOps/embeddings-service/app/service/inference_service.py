from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue

from app.service.embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class _BatchRequest:
    texts: list[str]
    result_container: list[tuple[list[list[float]] | None, BaseException | None]] = field(
        default_factory=lambda: [(None, None)]
    )
    done: threading.Event = field(default_factory=threading.Event)


class InferenceService:
    """Inference service with optional dynamic batching via queue + worker."""

    def __init__(
        self,
        embedder: Embedder,
        *,
        max_batch_size: int = 32,
        batch_window_ms: int = 1000,
        batching_enabled: bool = True,
    ) -> None:
        self._embedder = embedder
        self._max_batch_size = max_batch_size
        self._batch_window_sec = batch_window_ms / 1000.0
        self._batching_enabled = batching_enabled

        self._queue: Queue[_BatchRequest | None] = Queue()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        if batching_enabled:
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=False)
            self._worker_thread.start()
            logger.info(
                "Dynamic batching enabled: max_batch_size=%d, batch_window_ms=%d",
                max_batch_size,
                batch_window_ms,
            )

    def _worker_loop(self) -> None:
        """Background worker: collects requests and runs batched inference."""
        while not self._stop_event.is_set():
            batch: list[_BatchRequest] = []

            try:
                first = self._queue.get(timeout=0.1)
            except Empty:
                continue

            if first is None:
                return

            batch.append(first)
            total_texts = sum(len(r.texts) for r in batch)
            deadline = time.monotonic() + self._batch_window_sec

            while total_texts < self._max_batch_size and time.monotonic() < deadline:
                try:
                    item = self._queue.get(timeout=min(0.01, max(0.001, deadline - time.monotonic())))
                    if item is None:
                        self._queue.put(None)  # Restore shutdown signal for next iteration
                        break
                    batch.append(item)
                    total_texts += len(item.texts)
                except Empty:
                    break

            all_texts: list[str] = []
            boundaries: list[tuple[int, int]] = []

            for req in batch:
                start = len(all_texts)
                all_texts.extend(req.texts)
                boundaries.append((start, len(all_texts)))

            try:
                embeddings = self._embedder.embed(all_texts)
            except Exception as e:
                logger.exception("Embedder failed: %s", e)
                for req in batch:
                    req.result_container[0] = (None, e)
                    req.done.set()
                continue

            for req, (start, end) in zip(batch, boundaries):
                req.result_container[0] = (embeddings[start:end], None)
                req.done.set()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._batching_enabled:
            return self._embedder.embed(texts)

        req = _BatchRequest(texts=texts)
        self._queue.put(req)
        req.done.wait()
        result, error = req.result_container[0]
        if error is not None:
            raise error
        if result is None:
            raise RuntimeError("Worker did not set result")
        return result

    def shutdown(self) -> None:
        """Stop the worker thread. Call on app shutdown."""
        if self._worker_thread is None:
            return
        self._stop_event.set()
        self._queue.put(None)
        self._worker_thread.join(timeout=5.0)
        if self._worker_thread.is_alive():
            logger.warning("Worker thread did not stop within timeout")
