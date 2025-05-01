from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from mealpy.evolutionary_based.GA import BaseGA
from mealpy.utils.problem import FloatVar

"""
Algoritm de planificare a intervențiilor chirurgicale – versiune optimizată
-------------------------------------------------------------------------
Îmbunătățiri față de versiunea precedentă:
1. Prioritizare mai puternică a operațiilor curate
2. Gestionare optimizată a operațiilor lungi
3. Calcul mai precis al timpilor de curățare
4. Validări suplimentare pentru resurse
5. Testare mai robustă a constrângerilor
"""

# =====================
# —— CONSTANTE ————
# =====================
DAY_START = 8 * 60                # 08:00 în minute
DAY_END = 17 * 60                 # 17:00 în minute
LATE_PENALTY_COEFF = 0.5          # ponderarea lateness (pe ore)
DIRTY_CLEAN_GAP = 30              # diferența totală curat ↔ murdar (min)
CLEANING_TIME_CURATA = 10         # timp curățare operație curată
CLEANING_TIME_MURDARA = 30        # timp curățare operație murdară
UNSCHEDULED_PENALTY = 10_000      # penalizare „hard”
RESERVED_EMERGENCY_ROOMS = 0      # săli rezervate pentru urgențe
UNUSED_ROOM_PENALTY = 50          # penalizare pentru săli neutilizate
EARLY_LONG_SURGERY_BONUS = -20    # bonus pentru programarea devreme a operațiilor lungi (>2h)

# =====================
# —— ACCES SQLITE ——
# =====================

def fetch_data(selected_date: str) -> tuple[list[dict], list[dict]]:
    """Încărcăm sălile și intervențiile (status = 'in_asteptare') din SQLite."""
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    # Rooms
    c.execute(
        """
        SELECT NrSala, SalaMare, Laparo, Chirurgie
        FROM website_sali
        ORDER BY NrSala
        """
    )
    rooms = c.fetchall()

    # Surgeries to schedule
    c.execute(
    """
    SELECT e.id, e.nume_pacient, o.Nume, e.timp_estimare,
           e.data_interventie, e.user_id,
           u.first_name, u.last_name,
           o.Laparoscopic, o.OperatieCurata, o.NecesitaIntubare
    FROM calendarapp_event   e
    JOIN calendarapp_operatie o ON e.tip_operatie_id = o.id
    JOIN accounts_user u ON e.user_id = u.id
    WHERE strftime('%Y-%m-%d', e.data_interventie) = ?
      AND e.status = 'in_asteptare'
    ORDER BY e.id
    """,
    (selected_date,),
)
    surgeries = c.fetchall()
    conn.close()

    room_data = [
        {
            "id": r[0],
            "is_large": bool(r[1]),
            "laparoscopic": bool(r[2]),
            "chirurgie": r[3],
        }
        for r in rooms
    ]

    surgery_data = [
        {
            "id": s[0],
            "patient": s[1],
            "type": s[2],
            "duration": s[3],
            "date": s[4],
            "surgeon_id": s[5],
            "surgeon": f"{s[6]} {s[7]}",  # first_name + last_name
            "laparoscopic": bool(s[8]),
            "curata": bool(s[9]),
            "intubare": bool(s[10]),
            "is_long": s[3] > 120,
        }
        for s in surgeries
    ]
    return room_data, surgery_data

# =====================
# —— HELPERS ——
# =====================

def cleaning_minutes(surgery: Dict) -> int:
    """Returnează timpul de curățare (10/30 min)."""
    return CLEANING_TIME_CURATA if surgery["curata"] else CLEANING_TIME_MURDARA


def is_room_compatible(room: Dict, surgery: Dict) -> bool:
    """Verifică compatibilitatea sălii cu cerințele intervenției."""
    # Intervenția laparoscopică necesită sală echipată
    if surgery["laparoscopic"] and not room["laparoscopic"]:
        return False
    # Intubarea necesită sală mare
    if surgery["intubare"] and not room["is_large"]:
        return False
    return True


def next_slot(start: int, dur: int, intervals: List[Tuple[int, int]]) -> Optional[int]:
    """Cel mai devreme start care nu se suprapune peste intervalele existente."""
    cur = start
    idx = 0
    while True:
        while idx < len(intervals) and intervals[idx][1] <= cur:
            idx += 1
        if idx == len(intervals) or cur + dur <= intervals[idx][0]:
            return cur if cur + dur <= DAY_END else None
        cur = intervals[idx][1]
        if cur + dur > DAY_END:
            return None

# =====================
# —— CORE SCHEDULER ——
# =====================

def build_schedule(order: List[int], rooms: List[Dict], surgeries: List[Dict]) -> tuple[list[dict], float]:
    """Construiește programul și calculează costul pentru o permutare dată."""
    n_rooms = len(rooms)

    room_free: List[int] = [DAY_START] * n_rooms
    room_dirty: List[bool] = [False] * n_rooms  # True dacă sală a avut operație murdară
    room_schedules: List[list[dict]] = [[] for _ in range(n_rooms)]
    room_used: List[bool] = [False] * n_rooms  # Pentru penalizarea sălilor neutilizate

    surgeon_map: Dict[int, List[Tuple[int, int]]] = {}

    cost_idle = cost_clean = cost_late = 0
    dirty_penalty = 0
    unscheduled = 0
    bonus_early_long = 0

    for idx in order:
        s = surgeries[idx]
        dur = s["duration"]
        clean = cleaning_minutes(s)

        chosen_room = chosen_start = None
        best_room_score = float('inf')

        for r_idx, room in enumerate(rooms):
            # Verifică compatibilitatea sălii
            if not is_room_compatible(room, s):
                continue
            
            # Evită să programeze operații curate în săli murdare
            if room_dirty[r_idx] and s["curata"]:
                continue

            # Calculează cel mai devreme start posibil
            start_candidate = room_free[r_idx]
            start_candidate = next_slot(start_candidate, dur, surgeon_map.get(s["surgeon"], []))
            if start_candidate is None:
                continue
            
            # Verifică depășirea programului
            if start_candidate + dur + clean > DAY_END:
                continue

            # Calculează scorul pentru această sală
            room_score = start_candidate
            # Bonus pentru operații lungi programate devreme
            if s["is_long"] and start_candidate < DAY_START + 120:  # În primele 2 ore
                room_score += EARLY_LONG_SURGERY_BONUS
            # Penalizare pentru operații curate în săli care au avut deja operații murdare
            if room_dirty[r_idx] and s["curata"]:
                room_score += DIRTY_CLEAN_GAP * 2  # Penalizare dublă

            if room_score < best_room_score:
                best_room_score = room_score
                chosen_room, chosen_start = r_idx, start_candidate

        if chosen_room is None:
            unscheduled += 1
            continue

        # Actualizează programul
        end_time = chosen_start + dur
        prev_end = DAY_START if not room_schedules[chosen_room] else room_schedules[chosen_room][-1]["_end"]
        
        # Calculează costuri
        idle_time = max(0, chosen_start - prev_end)
        cost_idle += idle_time
        cost_clean += clean
        cost_late += ((chosen_start - DAY_START) / 60) * (dur / 60) * LATE_PENALTY_COEFF
        
        # Bonus pentru operații lungi programate devreme
        if s["is_long"] and chosen_start < DAY_START + 120:
            bonus_early_long += EARLY_LONG_SURGERY_BONUS

        # Penalizare pentru operații murdare
        if not s["curata"]:
            room_dirty[chosen_room] = True
            dirty_penalty += DIRTY_CLEAN_GAP

        # Salvează intrarea
        entry = {
            "id": s["id"],
            "type": s["type"],
            "start_time": f"{chosen_start//60}:{chosen_start%60:02d}",
            "end_time": f"{end_time//60}:{end_time%60:02d}",
            "surgeon": s["surgeon"],
            "patient": s["patient"],
            "duration": dur,
            "clean_time": clean,
            "is_clean": s["curata"],
            "_end": end_time,
        }

        room_schedules[chosen_room].append(entry)
        room_used[chosen_room] = True

        # Actualizează trackere
        room_free[chosen_room] = end_time + clean
        surgeon_map.setdefault(s["surgeon"], []).append((chosen_start, end_time))
        surgeon_map[s["surgeon"]].sort()

    # Calculează penalizări pentru săli neutilizate
    unused_penalty = sum(UNUSED_ROOM_PENALTY for used in room_used if not used)

    # Curăță câmpurile interne
    timetable: list[dict] = []
    for r_idx, sched in enumerate(room_schedules):
        for e in sched:
            e.pop("_end", None)
        timetable.append({
            "room": rooms[r_idx]["id"],
            "schedule": sched,
            "total_used": (room_free[r_idx] - DAY_START) if room_used[r_idx] else 0
        })

    # Cost total
    total_cost = (
        cost_idle
        + cost_clean
        + cost_late
        + dirty_penalty
        + UNSCHEDULED_PENALTY * unscheduled
        + unused_penalty
        + bonus_early_long
    )
    return timetable, total_cost

# =====================
# —— GENETIC ALG. ——
# =====================

def solve_ga(rooms: List[Dict], surgeries: List[Dict], epoch: int = 500, pop: int = 80):
    """Rezolvă programarea prin algoritm genetic."""
    n = len(surgeries)
    bounds = FloatVar(lb=[0.0] * n, ub=[1.0] * n, name="rk")

    def fitness(sol):
        perm = sorted(range(n), key=lambda i: sol[i])
        _, cost = build_schedule(perm, rooms, surgeries)
        return cost

    model = BaseGA(epoch=epoch, pop_size=pop, pc=0.9, pm=0.2)
    problem = {"obj_func": fitness, "bounds": bounds, "minmax": "min"}
    best = model.solve(problem)
    best_perm = sorted(range(n), key=lambda i: best.solution[i])
    timetable, _ = build_schedule(best_perm, rooms, surgeries)
    return timetable

# =====================
# —— API PUBLIC ——
# =====================


def schedule_surgeries(selected_date: str):
    """
    Generează programul operațiilor pentru ziua aleasă.
    — rezervăm PRIMA sală mare (is_large=True) pentru urgențe;
    — ea apare în grafic cu un bloc „Rezervată pentru urgențe”,
      dar NU este folosită de algoritmul genetic.
    """
    # 0. date brute
    rooms, surgeries = fetch_data(selected_date)

    # 1. găsim prima sală mare
    emergency_room = next((r for r in rooms if r["is_large"]), None)

    # 2. lista pentru GA = toate sălile, mai puţin cea de urgenţe (dacă există)
    if emergency_room:
        rooms_for_ga = [r for r in rooms if r["id"] != emergency_room["id"]]
    else:
        rooms_for_ga = rooms

    # 3. rulează optimizarea (doar pe sălile elective)
    if surgeries:
        timetable = solve_ga(rooms_for_ga, surgeries)
    else:
        timetable = []

    # 4. adaugă rândul special pentru sală „Rezervată”
    if emergency_room:
        dummy_event = {
        "id": None,
        "type": "Rezervată pentru urgențe",
        "start_time": f"{DAY_START // 60:02d}:{DAY_START % 60:02d}",
        "end_time":   f"{DAY_END   // 60:02d}:{DAY_END   % 60:02d}",
        "duration": DAY_END - DAY_START,
        "clean_time": 0,
        "is_clean": True,
        "reserved": True,              # marcaj ca să-l detectezi în template
        "css_class": "emergency-slot", # class extra pentru stil
}

        timetable.append(
            {
                "room": emergency_room["id"],
                "schedule": [dummy_event],
                "total_used": 0,
                "reserved_emergency": True,   # câmp auxiliar (front-end poate ignora)
            }
        )
        # ordonează rândurile după numărul sălii, ca să păstrezi afișarea firească
        timetable.sort(key=lambda x: x["room"])

    return timetable


# =====================
# —— TEST ——
# =====================
if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Running surgical scheduler for {today}")
    timetable = schedule_surgeries(today)
    
    print("\nResulting Schedule:")
    for room in timetable:
        print(f"\nRoom {room['room']} (Total used: {room['total_used']} minutes):")
        for event in room["schedule"]:
            print(f"  {event['start_time']}-{event['end_time']}: {event['type']} "
                  f"(Patient: {event['patient']}, Surgeon: {event['surgeon']}, "
                  f"Clean: {event['clean_time']}min)")