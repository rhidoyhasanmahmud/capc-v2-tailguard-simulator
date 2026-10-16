from __future__ import annotations

from collections.abc import Iterable, Iterator

from capc_sim.model.transaction import Transaction


class CoordinationQueue:
    """Deterministic pending cross-shard transaction queue.

    The queue owns storage only. It deliberately contains no scheduling policy;
    schedulers receive a read-only snapshot and choose among candidates.
    """

    def __init__(self) -> None:
        self._items: list[Transaction] = []

    def enqueue(self, tx: Transaction) -> None:
        if tx in self._items:
            raise ValueError(f"Transaction {tx.transaction_id} is already queued")
        self._items.append(tx)

    def remove(self, tx: Transaction) -> None:
        self._items.remove(tx)

    def snapshot(self) -> tuple[Transaction, ...]:
        return tuple(self._items)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __iter__(self) -> Iterator[Transaction]:
        return iter(self._items)

    def __contains__(self, tx: object) -> bool:
        return tx in self._items

    def extend_for_test(self, txs: Iterable[Transaction]) -> None:
        """Testing helper; normal simulation enqueues transactions one at a time."""
        for tx in txs:
            self.enqueue(tx)
