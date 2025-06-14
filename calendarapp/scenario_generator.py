

import random
from datetime import datetime

def generate_synthetic_rooms(n_rooms: int) -> list[dict]:
    rooms = []
    for r in range(n_rooms):
        room = {
            "id": r,
            "is_large": r < max(1, n_rooms // 4),  # ~25% mari
            "laparoscopic": r < max(1, n_rooms // 2),  # ~50% cu laparoscopie
            "chirurgie": f"Specialitate_{random.randint(1,4)}",
            "reserved_for_emergency": r == 0
        }
        rooms.append(room)
    return rooms

import random
from datetime import datetime

def generate_synthetic_surgeries(n: int, pct_long: float, available_rooms: list[dict], n_surgeons: int) -> list[dict]:
    """
    Generează o listă de intervenții chirurgicale sintetice, calibrate realist.
    """
    surgeries = []
    n_long = int(n * pct_long)

    has_lap = any(r["laparoscopic"] for r in available_rooms)
    has_large = any(r["is_large"] for r in available_rooms)

    for i in range(n):
        is_long = i < n_long

        # 1. Durată: realistă
        if is_long:
            duration = int(random.gauss(200, 20))  # lungă: 150±20 min
        else:
            duration = int(random.gauss(60, 15))   # scurtă: 70±15 min
        duration = max(30, duration)               # min 30 min

        # 2. Atribute intervenție
        laparoscopic = has_lap and random.random() < 0.3      # ~30%
        intubare = has_large and random.random() < 0.1        # ~10%
        murdara = random.random() < 0.15                      # ~15%
        buffer_time = 30 if murdara else 10

        # 3. Complexitate: bazată pe durată
        complexity = 3 if duration >= 120 else random.choice([1, 2])

        # 4. Prioritate
        priority = 3 if (complexity == 3) else \
           2 if duration >= 90 else \
           1

        surgery = {
            "id": i,
            "patient": f"Pacient_{i}",
            "type": f"TipOp_{random.randint(1,10)}",
            "duration": duration,
            "buffer": buffer_time,
            "date": datetime.today(),
            "surgeon_id": random.randint(1, n_surgeons),
            "surgeon": f"Dr.{random.choice(['Popescu','Ionescu','Georgescu','Florescu','Antonescu'])}",
            "laparoscopic": laparoscopic,
            "curata": not murdara,
            "intubare": intubare,
            "complexity": complexity,
            "priority": priority,
            "is_long": is_long,
            "early_pref": is_long or intubare or murdara,
            "window_preference": "AM" if is_long or intubare else random.choice(["AM", "PM"])
        }
        surgeries.append(surgery)

    random.shuffle(surgeries)
    return surgeries

def generate_synthetic_nurses(n_nurses: int) -> list[dict]:
    return [{"id": i, "name": f"Asistenta_{i}"} for i in range(n_nurses)]

def generate_nurse_alloc(num_surgeries: int, num_nurses: int) -> list[int]:
    base = [i % num_nurses for i in range(num_surgeries)]
    random.shuffle(base)
    return base

