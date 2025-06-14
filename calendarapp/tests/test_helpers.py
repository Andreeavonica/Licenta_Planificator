# calendarapp/tests/test_helpers.py
import pytest

from calendarapp.optimization import cleaning_minutes, is_room_compatible, next_slot, DAY_END

@pytest.mark.parametrize("curata,expected", [
    (True, 10),   # timpul definit pentru curățenie "curata"
    (False, 30),  # timpul definit pentru curățenie "murdara"
])
def test_cleaning_minutes(curata, expected):
    surgery = {"curata": curata}
    assert cleaning_minutes(surgery) == expected

@pytest.mark.parametrize("room,surgery,compatible", [
    ({"laparoscopic": True,  "is_large": True},  {"laparoscopic": True,  "intubare": False}, True),
    ({"laparoscopic": False, "is_large": True},  {"laparoscopic": True,  "intubare": False}, False),
    ({"laparoscopic": True,  "is_large": False}, {"laparoscopic": False, "intubare": True},  False),
    ({"laparoscopic": True,  "is_large": True},  {"laparoscopic": False, "intubare": False}, True),
])
def test_is_room_compatible(room, surgery, compatible):
    assert is_room_compatible(room, surgery) is compatible



def test_next_slot_no_room():
    # dacă nu încape până la DAY_END
    # presupunem că DAY_END = 17*60 = 1020
    # dacă start + duration depășește 1020, se întoarce None
    assert next_slot(DAY_END - 30, 60, []) is None
