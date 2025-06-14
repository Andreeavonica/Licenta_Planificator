
# calendarapp/tests/test_schedule_surgeries_no_ops.py
import os
import json
from unittest.mock import patch
from calendarapp.optimization import schedule_surgeries
@patch("calendarapp.optimization.fetch_data")
def test_surgery_too_long_unscheduled(mock_fetch_data):
    date = "2025-12-17"
    rooms = [{"id": 1, "is_large": True, "laparoscopic": True}]
    surgeries = [{
        "id": 1, "patient": "P", "type": "MegaOp",
        "duration": 600,  # 10h (ziua are 9h)
        "date": date, "surgeon_id": 1, "surgeon": "DrLung",
        "laparoscopic": False, "curata": False,
        "intubare": False, "complexity": 1, "priority": 1, "is_long": True,
    }]
    nurses = [{"id": 1, "name": "N"}]
    mock_fetch_data.return_value = (rooms, surgeries, nurses)

    timetable = schedule_surgeries(date)
    neplanificate = [r for r in timetable if r["room"] == "neplanificate"]
    assert neplanificate, "Operația nu a fost marcată neplanificată"
