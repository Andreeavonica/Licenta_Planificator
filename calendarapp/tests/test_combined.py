import pytest
from unittest.mock import patch

import numpy as np

from calendarapp.optimization import (
    cleaning_minutes,
    is_room_compatible,
    next_slot,
    repair_chromosome_light,
    build_schedule,
    solve_ga,
    schedule_surgeries,
    DAY_START,
    DAY_END,
)


# --- FIXTURES PENTRU DATE EXEMPLU ---

@pytest.fixture
def rooms():
    return [
        {"id": 1, "is_large": True, "laparoscopic": True, "chirurgie": True},
        {"id": 2, "is_large": False, "laparoscopic": False, "chirurgie": False},
    ]

@pytest.fixture
def nurses():
    return [{"id": 0, "name": "N1"}, {"id": 1, "name": "N2"}]

@pytest.fixture
def base_surgery():
    return {
        "id": 10,
        "patient": "P",
        "type": "T",
        "duration": 60,
        "date": "2025-12-23",
        "surgeon_id": 5,
        "surgeon": "Dr X",
        "laparoscopic": False,
        "curata": True,
        "intubare": False,
        "complexity": 1,
        "priority": 1,
        "is_long": False,
    }

@pytest.fixture
def surgeries(base_surgery):
    a = dict(base_surgery, id=1, type="HighPrio", priority=3)
    b = dict(base_surgery, id=2, type="LowPrio",  priority=1)
    return [a, b]


# --- 1) TESTE HELPER ---

def test_cleaning_minutes():
    s1 = {"curata": True}
    s2 = {"curata": False}
    assert cleaning_minutes(s1) == 10
    assert cleaning_minutes(s2) == 30

def test_is_room_compatible():
    room = {"is_large": True, "laparoscopic": True}
    s1 = {"laparoscopic": True, "intubare": False}
    s2 = {"laparoscopic": True, "intubare": True}
    s3 = {"laparoscopic": False, "intubare": True}
    # laparo req met
    assert is_room_compatible(room, s1)
    # intubare → sală mare ok
    assert is_room_compatible(room, s2)
    # dacă sală nu e mare:
    room_small = {"is_large": False, "laparoscopic": True}
    assert not is_room_compatible(room_small, s2)
    # laparo false, intubare true + small room → nu compatibil
    assert not is_room_compatible(room_small, s3)

def test_next_slot_simple():
    # fără intervale ocupate, ar trebui să se plaseze imediat
    assert next_slot(DAY_START, 30, []) == DAY_START
    # ocupat 8:00-9:00 → primul slot liber e 9:00
    occupied = [(DAY_START, DAY_START + 60)]
    assert next_slot(DAY_START, 30, occupied) == DAY_START + 60
    # nu încape (peste zi)
    assert next_slot(DAY_END - 20, 30, []) is None


# --- 2) TESTE repair_chromosome_light ---

def test_repair_chromosome_light_no_conflict(rooms, surgeries):
    order = [0,1]
    # ambele încap fără probleme → rămâne aceeaşi ordine
    out = repair_chromosome_light(order, surgeries, rooms)
    assert out == order

def test_repair_chromosome_light_incompatible_room(rooms, surgeries):
    # marchez prima intervenție laparoscopică pe sală fără laparo → va fi unplaced
    surgeries[0]["laparoscopic"] = True
    # room[1] nu are laparo, room[0] da → dar ordinea începe cu idx 1
    order = [1,0]
    out = repair_chromosome_light(order, surgeries, rooms)
    # 1 e plasat, 0 pus la final
    assert out == [1,0]


# --- 3) TESTE build_schedule ---

def test_build_schedule_single(rooms, nurses, base_surgery):
    # o singură intervenție, order=[0], alocare nurse=[0]
    tt, cost = build_schedule([0], [rooms[0]], [base_surgery], [0], nurses)
    # ar trebui să fie programată la 08:00-09:00
    sched = tt[0]["schedule"][0]
    assert sched["start_time"] == "8:00"
    assert sched["end_time"]   == "9:00"
    # cost > 0 (curățenie + idle etc)
    assert cost > 0

def test_build_schedule_respects_order(rooms, surgeries, nurses):
    # două intervenții, le punem invers → și programarea urmează ordinea
    order = [1,0]
    nurse_alloc = [0,0]
    tt, _ = build_schedule(order, [rooms[0]], surgeries, nurse_alloc, nurses)
    types = [e["type"] for e in tt[0]["schedule"]]
    assert types == ["LowPrio", "HighPrio"]

def test_build_schedule_unscheduled_if_no_room(rooms, nurses, base_surgery):
    # facem duration prea mare ca să nu încapă
    big = dict(base_surgery, duration=(DAY_END - DAY_START) + 1, id=99, type="X")
    tt, _ = build_schedule([0], [rooms[1]], [big], [0], nurses)
    # ar trebui să apară rând 'neplanificate'
    assert any(row["room"] == "neplanificate" for row in tt)




# --- 5) TEST schedule_surgeries integrat ---

@patch("calendarapp.optimization.fetch_data")
@patch("calendarapp.optimization.solve_ga")
def test_schedule_surgeries_flow(mock_ga, mock_fetch, rooms, surgeries, nurses):
    # pregătim datele returnate de fetch_data
    mock_fetch.return_value = (rooms, surgeries, nurses)
    # stub pentru solve_ga: vrem un slot clar
    fake = [{"room": 1, "schedule": [{"id":1,"type":"X","start_time":"08:00","end_time":"09:00"}]}]
    mock_ga.return_value = fake
    out = schedule_surgeries("2025-12-23")
    # ar trebui să fie exact fake + eventual sala de urgență
    assert fake[0] in out
