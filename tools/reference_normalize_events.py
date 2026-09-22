from __future__ import annotations

import copy
import unittest
from typing import Any


def normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    newest_by_id: dict[Any, dict[str, Any]] = {}
    for event in events:
        if "id" not in event:
            raise ValueError("Event is missing id")
        if "timestamp" not in event:
            raise ValueError("Event is missing timestamp")
        event_id = event["id"]
        current = newest_by_id.get(event_id)
        if current is None or event["timestamp"] > current["timestamp"]:
            newest_by_id[event_id] = copy.deepcopy(event)
    return sorted(
        newest_by_id.values(),
        key=lambda event: (event["timestamp"], event["id"]),
    )


class TestNormalizeEvents(unittest.TestCase):
    def test_empty_input(self) -> None:
        self.assertEqual(normalize_events([]), [])

    def test_single_event_and_field_preservation(self) -> None:
        event = {
            "id": "a",
            "timestamp": 1,
            "payload": {"value": 3},
            "metadata": {"source": "test"},
        }
        self.assertEqual(normalize_events([event]), [event])

    def test_sorting_and_equal_timestamp_id_tie_break(self) -> None:
        events = [
            {"id": "b", "timestamp": 2},
            {"id": "z", "timestamp": 1},
            {"id": "a", "timestamp": 1},
        ]
        self.assertEqual(
            normalize_events(events),
            [
                {"id": "a", "timestamp": 1},
                {"id": "z", "timestamp": 1},
                {"id": "b", "timestamp": 2},
            ],
        )

    def test_newest_duplicate_wins(self) -> None:
        self.assertEqual(
            normalize_events(
                [
                    {"id": "a", "timestamp": 1, "payload": "old"},
                    {"id": "a", "timestamp": 3, "payload": "new"},
                ]
            ),
            [{"id": "a", "timestamp": 3, "payload": "new"}],
        )

    def test_invalid_records(self) -> None:
        with self.assertRaisesRegex(ValueError, "id"):
            normalize_events([{"timestamp": 1}])
        with self.assertRaisesRegex(ValueError, "timestamp"):
            normalize_events([{"id": "a"}])

    def test_input_immutability_and_determinism(self) -> None:
        events = [{"id": "a", "timestamp": 1, "payload": {"x": 1}}]
        original = copy.deepcopy(events)
        first = normalize_events(events)
        second = normalize_events(events)
        self.assertEqual(events, original)
        self.assertIsNot(first, events)
        self.assertIsNot(first[0], events[0])
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
