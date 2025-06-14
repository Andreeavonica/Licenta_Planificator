import sys, os, random, json, django
from unittest.mock import patch

# ✅ Setup Django corect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventcalendar.settings")
django.setup()

# ✅ Importă doar după setup
from calendarapp.optimization import schedule_surgeries

@patch("calendarapp.optimization.fetch_data")
def test_schedule_with_strict_validation(mock_fetch_data):
    selected_date = "2025-10-15"

    # Generate 3 operating rooms
    rooms = [{"id": i, "is_large": True, "laparoscopic": True, "chirurgie": "A"} for i in range(1, 4)]

    # Generate 5 nurses
    nurses = [{"id": 100 + i, "name": f"Nurse {i}"} for i in range(5)]

    # Generate 10 diverse surgeries
    surgeries = []
    for i in range(10):
        dur = random.choice([90, 120, 150])
        surgeries.append({
            "id": 200 + i,
            "patient": f"Patient {i}",
            "type": f"Procedure {i}",
            "duration": dur,
            "date": selected_date,
            "surgeon_id": 300 + i % 2,
            "surgeon": f"Dr. {i % 2}",
            "laparoscopic": bool(i % 2),
            "curata": bool(i % 3),
            "intubare": bool(i % 4 == 0),
            "complexity": (i % 3) + 1,
            "priority": (i % 2) + 1,
            "is_long": dur > 120,
        })

    # Inject synthetic data
    mock_fetch_data.return_value = (rooms, surgeries, nurses)

    # Run scheduler
    timetable = schedule_surgeries(selected_date)

    # ✅ Assert all rooms have schedule keys
    assert isinstance(timetable, list)
    assert all("schedule" in r for r in timetable)

    # ✅ Assert all surgeries were scheduled or marked explicitly as unplanned
    total_ops = sum(len(r["schedule"]) for r in timetable)
    assert total_ops == len(surgeries), "Not all surgeries were returned in schedule!"

    # ✅ Assert no surgeon has overlapping surgeries (only for planned ones)
    surgeon_timetable = {}
    for room in timetable:
        for op in room["schedule"]:
            if "start_time" not in op or "end_time" not in op:
                continue  # 🛑 skip unplanned ops
            surgeon = op["surgeon"]
            start = int(op["start_time"].split(":" )[0]) * 60 + int(op["start_time"].split(":" )[1])
            end = int(op["end_time"].split(":" )[0]) * 60 + int(op["end_time"].split(":" )[1])
            surgeon_timetable.setdefault(surgeon, []).append((start, end))

    for surgeon, times in surgeon_timetable.items():
        times.sort()
        for i in range(1, len(times)):
            assert times[i][0] >= times[i-1][1], f"Overlap detected for surgeon {surgeon}"

    # ✅ Save output for review
    os.makedirs("output", exist_ok=True)
    with open("output/timetable_strict.json", "w", encoding="utf-8") as f:
        json.dump(timetable, f, indent=2, ensure_ascii=False)

    # ✅ Log neplanificate
    for r in timetable:
        if r["room"] == "neplanificata":
            print("\n🟥 Operații neplanificate:")
            for op in r["schedule"]:
                print(f"- {op['type']} by {op['surgeon']} ({op['duration']} min)")

    print("\n✅ Scheduler test passed: all surgeries handled correctly.")
