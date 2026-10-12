"""Implement these three ring operations before running check.py."""

import torch
import torch.distributed as dist


def ring_reduce_scatter(tensor):
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    chunks = [chunk.clone() for chunk in tensor.chunk(world_size)]

    # TODO: обменять части по кольцу, сложить их и вернуть chunks[rank].
    left = (rank - 1) % world_size
    right = (rank + 1) % world_size

    for step in range(world_size - 1):
        send_idx = (rank - step - 1) % world_size
        recv_idx = (rank - step - 2) % world_size

        received = torch.empty_like(chunks[recv_idx])

        send_req = dist.isend(chunks[send_idx], dst=right)
        recv_req = dist.irecv(received, src=left)

        send_req.wait()
        recv_req.wait()

        chunks[recv_idx].add_(received)
    
    return chunks[rank]


def ring_all_gather(shard):
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    chunks = [torch.empty_like(shard) for _ in range(world_size)]
    chunks[rank].copy_(shard)

    # TODO: передать части по кольцу и вернуть torch.cat(chunks).
    left = (rank - 1) % world_size
    right = (rank + 1) % world_size

    for step in range(world_size - 1):
        send_idx = (rank - step) % world_size
        recv_idx = (rank - step - 1) % world_size

        send_req = dist.isend(chunks[send_idx], dst=right)
        recv_req = dist.irecv(chunks[recv_idx], src=left)

        send_req.wait()
        recv_req.wait()

    return torch.cat(chunks, dim=0)


def ring_all_reduce(tensor):
    shard = ring_reduce_scatter(tensor)
    return ring_all_gather(shard)
