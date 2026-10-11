"""Implement these three ring operations before running check.py."""

import torch
import torch.distributed as dist


def ring_reduce_scatter(tensor):
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    chunks = [chunk.clone() for chunk in tensor.chunk(world_size)]

    # TODO: обменять части по кольцу, сложить их и вернуть chunks[rank].
    raise NotImplementedError("ring_reduce_scatter")


def ring_all_gather(shard):
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    chunks = [torch.empty_like(shard) for _ in range(world_size)]
    chunks[rank].copy_(shard)

    # TODO: передать части по кольцу и вернуть torch.cat(chunks).
    raise NotImplementedError("ring_all_gather")


def ring_all_reduce(tensor):
    # TODO: последовательно вызвать две функции выше; вернуть сумму, не среднее.
    raise NotImplementedError("ring_all_reduce")
