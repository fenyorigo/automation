from __future__ import annotations

from typing import Any, Iterable


def connected_room_groups(
    room_ids: Iterable[int], contacts: Iterable[dict[str, Any]]
) -> list[set[int]]:
    """Return the current thermal room groups formed by open interior doors.

    An interior contact joins its two rooms only when it is explicitly open and
    not explicitly unavailable. Closed, unknown and unavailable contacts keep
    the rooms separated. Exterior contacts never alter the topology.
    """
    parents = {int(room_id): int(room_id) for room_id in room_ids}

    def find(room_id: int) -> int:
        while parents[room_id] != room_id:
            parents[room_id] = parents[parents[room_id]]
            room_id = parents[room_id]
        return room_id

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for contact in contacts:
        if contact.get("device_type") != "contact_sensor":
            continue
        if contact.get("opening_role") != "internal":
            continue
        if contact.get("online") is False or contact.get("zigbee_contact_closed") is not False:
            continue
        left = contact.get("room_id")
        right = contact.get("connected_room_id")
        if left is None or right is None:
            continue
        left, right = int(left), int(right)
        if left in parents and right in parents:
            union(left, right)

    groups: dict[int, set[int]] = {}
    for room_id in parents:
        groups.setdefault(find(room_id), set()).add(room_id)
    return sorted(groups.values(), key=lambda group: min(group))
