# calendarapp/tests/test_schedule_surgeries_no_ops.py
import os
import json
from unittest.mock import patch
from calendarapp.optimization import schedule_surgeries

@patch("calendarapp.optimization.fetch_data")
def test_schedule_surgeries_no_ops(mock_fetch_data):
    """
    Când nu există niciună intervenție programată,
    ar trebui să primim o listă cu o singură "emergency room"
    care are exact un element 08:00–17:00 și nimic altceva.
    """
    # Pregătim un singur salon (care va deveni emergency room în scheduler)
    rooms = [{"id": 99, "is_large": True, "laparoscopic": False, "chirurgie": "X"}]
    # Fără operații și fără asistente
    mock_fetch_data.return_value = (rooms, [], [])

    timetable = schedule_surgeries("2025-10-20")

    # Ar trebui să existe exact 1 rând
    assert isinstance(timetable, list)
    assert len(timetable) == 1

    row = timetable[0]
    # E sala de urgență
    assert row.get("reserved_emergency") is True

    # Și programul rezervat este 08:00–17:00
    sched = row["schedule"]
    assert len(sched) == 1
    ev = sched[0]
    assert ev["start_time"] == "08:00"
    assert ev["end_time"]   == "17:00"

    # Opțional: scriem fișier pentru inspecție manuală
    os.makedirs("output", exist_ok=True)
    with open("output/timetable_no_ops.json", "w", encoding="utf-8") as f:
        json.dump(timetable, f, indent=2, ensure_ascii=False)
