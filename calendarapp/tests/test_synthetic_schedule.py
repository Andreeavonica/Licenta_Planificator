import django
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventcalendar.settings")
django.setup()
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from unittest.mock import patch
from calendarapp.optimization import schedule_surgeries
import random


@patch("calendarapp.optimization.fetch_data")
def test_schedule_with_generated_data(mock_fetch_data):
    selected_date = "2025-10-15"

    # — Generate 3 rooms —
    rooms = [{"id": i, "is_large": i % 2 == 0, "laparoscopic": i != 2, "chirurgie": "A"} for i in range(1, 4)]

    # — Generate 5 nurses —
    nurses = [{"id": 100 + i, "name": f"Nurse {i}"} for i in range(5)]

    # — Generate 10 surgeries —
    surgeries = []
    for i in range(10):
        dur = random.choice([60, 90, 120, 150])
        surgeries.append({
            "id": 200 + i,
            "patient": f"Patient {i}",
            "type": f"OpType {i}",
            "duration": dur,
            "date": selected_date,
            "surgeon_id": 300 + i % 2,
            "surgeon": f"Dr. {i % 2}",
            "laparoscopic": i % 2 == 0,
            "curata": i % 3 != 0,
            "intubare": i % 4 == 0,
            "complexity": (i % 3) + 1,
            "priority": (i % 2) + 1,
            "is_long": dur > 120,
        })

    # — Inject mock —
    mock_fetch_data.return_value = (rooms, surgeries, nurses)

    # — Call function —
    timetable = schedule_surgeries(selected_date)

    # — Validate —
    assert isinstance(timetable, list)
    assert all("schedule" in r for r in timetable)
    print("\nTimetable result with synthetic data:")
    for r in timetable:
        print(f"Room {r['room']}: {len(r['schedule'])} ops")
