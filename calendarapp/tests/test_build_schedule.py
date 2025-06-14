# calendarapp/tests/test_build_schedule.py
from calendarapp.optimization import build_schedule

def test_build_schedule_surgeon_conflict():
    rooms = [{"id": 1, "is_large": True, "laparoscopic": True, "chirurgie": "A"}]
    surgeons = ["Dr A", "Dr A"]
    surgeries = []
    for i in range(2):
        # facem fiecare operație suficient de lungă încât a doua să nu mai încapă
        surgeries.append({
            "id": i,
            "duration": 300,   # 5 ore
            "surgeon": surgeons[i],
            "laparoscopic": False,
            "intubare": False,
            "curata": True,
            "complexity": 1,
            "priority": 1,
            "is_long": True,
            "type": f"T{i}",
            "patient": f"P{i}"
        })

    nurses = [{"id": 1, "name": "N"}]
    order = [0, 1]
    nurse_alloc = [0, 0]

    timetable, cost = build_schedule(order, rooms, surgeries, nurse_alloc, nurses)

    # Acum a doua nu mai încape → apare în neplanificate
    assert any(r["room"] == "neplanificate" for r in timetable), \
        "Operația conflictuală ar trebui să fie pusă la neplanificate"
