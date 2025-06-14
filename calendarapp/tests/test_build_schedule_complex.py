# calendarapp/tests/test_schedule_surgeries_surgeon_no_overlap.py
import os
import json
from unittest.mock import patch
import pytest
from calendarapp.optimization import schedule_surgeries

@patch("calendarapp.optimization.fetch_data")
def test_surgeon_no_overlap_across_rooms(mock_fetch_data):
    """
    Avem 2 săli identice și 2 intervenții simultane pentru același chirurg:
      - Una durează 120', cealaltă tot 120'.
    Doar una poate fi programată la 08:00–10:00, cealaltă trebuie să fie:
      a) fie programată mai târziu (dacă încap), 
      b) fie marcată neplanificată.
    Verificăm că nu există suprapunere în orarul global al chirurgului.
    """
    date = "2025-12-15"
    rooms = [
        {"id": 1, "is_large": True, "laparoscopic": True,  "chirurgie": "A"},
        {"id": 2, "is_large": True, "laparoscopic": True,  "chirurgie": "A"},
    ]
    # Două operații simultane, același surgeon
    surgeries = []
    for i in (0, 1):
        surgeries.append({
            "id": 300 + i,
            "patient": f"P{i}",
            "type":    f"T{i}",
            "duration": 120,  # 2h
            "date":     date,
            "surgeon_id": 42,
            "surgeon":   "DrOverlap",
            "laparoscopic": False,
            "curata":     True,
            "intubare":   False,
            "complexity": 1,
            "priority":   1,
            "is_long":    True,
        })
    nurses = [{"id": 9, "name": "N"}]
    mock_fetch_data.return_value = (rooms, surgeries, nurses)

    timetable = schedule_surgeries(date)

    # colectăm slot-urile planificate pe chirurg
    surgeon_slots = []
    for row in timetable:
        for op in row["schedule"]:
            if op.get("surgeon") == "DrOverlap" and "start_time" in op:
                h1, m1 = map(int, op["start_time"].split(":"))
                h2, m2 = map(int, op["end_time"].split(":"))
                start = h1*60 + m1
                end   = h2*60 + m2
                surgeon_slots.append((start, end))

    # verificăm că nu există suprapuneri
    surgeon_slots.sort()
    for (s1,e1), (s2,e2) in zip(surgeon_slots, surgeon_slots[1:]):
        assert s2 >= e1, f"Suprapunere pentru DrOverlap: {s1}-{e1} vs {s2}-{e2}"

    # dump JSON pentru inspecție manuală
    os.makedirs("output", exist_ok=True)
    with open("output/timetable_surgeon_overlap.json", "w", encoding="utf-8") as f:
        json.dump(timetable, f, indent=2, ensure_ascii=False)
