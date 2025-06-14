from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from mealpy.evolutionary_based.GA import BaseGA
from mealpy.utils.problem import FloatVar
from collections import defaultdict
from calendarapp.models import Event
from accounts.models import User

import numpy as np


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
COMPLEXITY_LATE_COEFF = 0.25     # ajustează după nevoi
COMPLEXITY_EARLY_BONUS = -20
PRIO_EARLY_BONUS = -30      # (minute) bonus negativ → trage operaţia importantă spre 08:00
PRIO_LATE_COEFF  = 0.8      # coef. suplimentar pentru lateness în funcţie de priority
PRIO_UNSCHED_P   = 15_000   

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
           o.Laparoscopic, o.OperatieCurata, o.NecesitaIntubare, o.grad_complexitate, e.prioritate
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

    room_data = [
        {
            "id": r[0],
            "is_large": int(r[1]) == 1,
            "laparoscopic": int(r[2]) == 1,
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
        "surgeon": f"{s[6]} {s[7]}",
        "laparoscopic": int(s[8]) == 1,
        "curata": int(s[9]) == 1,
        "intubare": int(s[10]) == 1,
        "complexity": int(s[11] or 1),
        "priority": int(s[12] or 2),
        "is_long": s[3] > 120,
    }
    for s in surgeries
]

    # Fetch nurses from DB (users with role = 'assistant')
    c = conn.cursor()
    c.execute("SELECT id, first_name, last_name FROM accounts_user WHERE role = 'assistant' AND is_active = 1")
    nurse_rows = c.fetchall()
    nurse_data = [{"id": r[0], "id": r[0], "name": f"{r[1]} {r[2]}"} for r in nurse_rows]
    conn.close()

    return room_data, surgery_data, nurse_data

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


def build_schedule(
    order: List[int],
    rooms: List[Dict],
    surgeries: List[Dict],
    nurse_alloc: List[int],
    nurses: List[Dict],
) -> tuple[list[dict], float]:
    """Planifică întreaga zi şi întoarce (timetable, cost total)."""

    # ─────---  iniţializări  ---─────
    room_free     = [DAY_START] * len(rooms)          # minutul de la care sala e liberă
    room_dirty    = [False] * len(rooms)
    room_schedules: list[list[dict]] = [[] for _ in rooms]
    room_used     = [False] * len(rooms)

    surgeon_map: dict[int, list[tuple[int, int]]] = {}        # suprapuneri chirurg
    nurse_map  : dict[int, list[tuple[int, int]]] = defaultdict(list)

    cost_idle = cost_clean = cost_late = 0
    dirty_penalty = bonus_early_long = 0
    cost_unsched = 0                 # <-- nou!
    nurse_use_count = [0] * len(nurses)

    unscheduled_events: list[dict] = []

    # ─────---  iterează intervenţiile în ordinea dată  ---─────
    for idx in order:
        s = surgeries[idx]
        dur   = s["duration"]
        clean = cleaning_minutes(s)
        nurse_id = nurse_alloc[idx]

        chosen_room = chosen_start = None
        best_room_score = float("inf")

        # ----- evaluează fiecare sală -----
        for r_idx, room in enumerate(rooms):
            if not is_room_compatible(room, s):
                continue

            start_candidate = next_slot(room_free[r_idx], dur, surgeon_map.get(s["surgeon"], []))
            if (
                start_candidate is None
                or next_slot(start_candidate, dur, nurse_map[nurse_id]) != start_candidate
                or start_candidate + dur + clean > DAY_END
            ):
                continue

            room_score = start_candidate

            # ① bonus pt intervenţii lungi puse devreme
            if s["is_long"] and start_candidate < DAY_START + 120:
                room_score += EARLY_LONG_SURGERY_BONUS

            # ② penalizare supl. dacă sala e „murdară” iar operaţia e curată
            if room_dirty[r_idx] and s["curata"]:
                room_score += DIRTY_CLEAN_GAP * 2

            # ③ lateness ∝ complexity + priority
            lateness = max(0, start_candidate - DAY_START)
            room_score += lateness * (
                s["complexity"] * COMPLEXITY_LATE_COEFF + s["priority"] * PRIO_LATE_COEFF
            )

            # ④ bonus pentru start în primele 30 min din zi
            if start_candidate < DAY_START + 30:
                room_score += PRIO_EARLY_BONUS * s["priority"]

            # ⑤ bonus supl. pentru operaţii curate, complexe, puse foarte devreme
            if s["curata"] and s["complexity"] >= 2 and start_candidate < DAY_START + 60:
                room_score += COMPLEXITY_EARLY_BONUS * s["complexity"]

            if room_score < best_room_score:
                best_room_score = room_score
                chosen_room, chosen_start = r_idx, start_candidate

        # ----- dacă NU avem sală liberă → marcat ca neprogramat -----
        if chosen_room is None:
            cost_unsched += PRIO_UNSCHED_P * (s["priority"] ** 2)
            unscheduled_events.append(
                {
                    "id": s.get("id"),
                    "type": s.get("type", "-"),
                    "duration": dur,
                    "surgeon": s.get("surgeon", "-"),
                    "patient": s.get("patient", "-"),
                    "unscheduled": True,
                }
            )
            continue

        # ----- programăm efectiv intervenţia -----
        end_time = chosen_start + dur
        prev_end = (
            DAY_START
            if not room_schedules[chosen_room]
            else room_schedules[chosen_room][-1]["_end"]
        )

        # actualizăm costuri
        cost_idle += max(0, chosen_start - prev_end)
        cost_clean += clean
        cost_late += (
            ((chosen_start - DAY_START) / 60)
            * (dur / 60)
            * LATE_PENALTY_COEFF
            * (s["complexity"] + s["priority"] * PRIO_LATE_COEFF)
        )
        if s["is_long"] and chosen_start < DAY_START + 120:
            bonus_early_long += EARLY_LONG_SURGERY_BONUS
        if not s["curata"]:
            room_dirty[chosen_room] = True
            dirty_penalty += DIRTY_CLEAN_GAP

        # salvăm în orar
        room_schedules[chosen_room].append(
            {
                "id": s["id"],
                "type": s["type"],
                "start_time": f"{chosen_start//60}:{chosen_start%60:02d}",
                "end_time": f"{end_time//60}:{end_time%60:02d}",
                "surgeon": s["surgeon"],
                "patient": s["patient"],
                "duration": dur,
                "clean_time": clean,
                "is_clean": s["curata"],
                "nurse": nurses[nurse_id]["name"],
                "nurse_id": nurses[nurse_id]["id"],
                "_end": end_time,
            }
        )

        # update registri
        room_used[chosen_room] = True
        room_free[chosen_room] = end_time + clean
        surgeon_map.setdefault(s["surgeon"], []).append((chosen_start, end_time))
        surgeon_map[s["surgeon"]].sort()
        nurse_map[nurse_id].append((chosen_start, end_time))
        nurse_map[nurse_id].sort()
        nurse_use_count[nurse_id] += 1

    # ─────---  construim output-ul  ---─────
    unused_penalty = sum(UNUSED_ROOM_PENALTY for used in room_used if not used)

    timetable = []
    for r_idx, sched in enumerate(room_schedules):
        for e in sched:
            e.pop("_end", None)           # nu expunem câmp intern
        timetable.append(
            {
                "room": rooms[r_idx]["id"],
                "schedule": sched,
                "total_used": (room_free[r_idx] - DAY_START) if room_used[r_idx] else 0,
            }
        )

    if unscheduled_events:
        timetable.append({"room": "neplanificate", "schedule": unscheduled_events, "total_used": 0})

    std_nurse = np.std(nurse_use_count)

    total_cost = (
        cost_idle
        + cost_clean
        + cost_late
        + dirty_penalty
        + cost_unsched           # <-- nou!
        + unused_penalty
        + bonus_early_long
        + std_nurse * 5
    )

    return timetable, total_cost



# =====================
# —— GENETIC ALG. ——
# =====================

def repair_chromosome_light(order: List[int], surgeries: List[Dict], rooms: List[Dict]) -> List[int]:
    """
    Repair-light de tip greedy: inserează pe rând fiecare intervenție în prima
    sală compatibilă și interval liber (fără suprapunere cu același chirurg),
    ținând un dicționar occupied pentru fiecare sală și surgeon_intervals
    pentru conflict chirurgical. Operațiile imposibil de plasat ajung la final.
    """
    # 1. Dizionar sală_id -> listă sortată de (start, end) ocupate (doar de operații)
    occupied_rooms: dict[int, List[Tuple[int, int]]] = {r["id"]: [] for r in rooms}
    # 2. Dizionar surgeon_id -> listă sortată de (start, end) ocupate
    surgeon_intervals: dict[int, List[Tuple[int, int]]] = {}
    # 3. Rezultatele:
    placed = []    # idx-urile programate (în ordinea “greedy” de inserție)
    unplaced = []  # idx-urile care nu s-au putut programa
    
    for idx in order:
        s = surgeries[idx]
        dur = s["duration"]
        clean = cleaning_minutes(s)
        surgeon_id = s["surgeon_id"]
        
        # Verificare rapidă: există vreo sală complet compatibilă (fără a testa interval)?
        # (Doar compatibilitate laparo/intubare + durata + cleaning încap în zi)
        if not any(
            is_room_compatible(room, s) and (DAY_START + dur + clean <= DAY_END)
            for room in rooms
        ):
            # Dacă nu încape clar în nicio sală (compatibilă + timp), îl considerăm imposibil.
            unplaced.append(idx)
            continue
        
        # 4. Încercăm să-l plasăm într-o sală compatibilă, în primul interval liber
        found_slot = False
        
        for room in rooms:
            room_id = room["id"]
            # 4.1. să fie compatibil OR <-> surgery
            if not is_room_compatible(room, s):
                continue
            
            # 4.2. Construim lista de intervale ocupate curente (fără curățenie)
            intervals_room = occupied_rooms[room_id]
            # 4.3. Din aceste intervale, calculăm lista “complementară” de intervale libere
            #      între DAY_START și DAY_END, FĂRĂ timpi de curățare.
            free_intervals = []
            prev_end = DAY_START
            for (st, en) in intervals_room:
                if prev_end + dur + clean <= st:
                    free_intervals.append((prev_end, st))
                prev_end = max(prev_end, en + cleaning_minutes(surgeries[0]))  
                # NOTĂ: aici nu trebuie curățenie globală, vom adăuga cleaning abia în build_schedule.
                #       Aici ne interesează doar slotul fără suprapunere operații.
            #  Încă trebuie să verificăm spațiul după ultima operație din sală
            if prev_end + dur + clean <= DAY_END:
                free_intervals.append((prev_end, DAY_END))
            
            # 4.4. Și verificăm pentru fiecare interval liber dacă se găsește un start posibil
            #      ținând cont și de suprapuneri cu chirurgul:
            #      pacientul începe în free_start, merge dur minute, apoi vrem clean minute la final
            for (free_start, free_end) in free_intervals:
                # Verificăm suprapuneri ale chirurgului:
                # surgeon_intervals.get(...) returnează liste sortate de (start, end).
                surgeon_list = surgeon_intervals.get(surgeon_id, [])
                # Folosim acel next_slot la nivel de surgeon:
                cand_start = next_slot(free_start, dur, surgeon_list)
                if cand_start is None or cand_start + dur + clean > free_end:
                    # nu încape corect fără suprapunere chirurg
                    continue
                # Am găsit momentul valid: cand_start, în sala room_id
                # ① adăugăm intervalul de operație în occupied_rooms (fără cleaning)
                occupied_rooms[room_id].append((cand_start, cand_start + dur))
                occupied_rooms[room_id].sort()  # păstrăm sortarea prin start-time
                # ② adăugăm și intervalul la surgeon_intervals
                surgeon_intervals.setdefault(surgeon_id, []).append((cand_start, cand_start + dur))
                surgeon_intervals[surgeon_id].sort()
                
                placed.append(idx)
                found_slot = True
                break
            
            if found_slot:
                break
        
        if not found_slot:
            # Nu a găsit nicio sală și interval liber compatibil chirurg/durată + cleaning
            unplaced.append(idx)
    
    # 5. Returnăm lista finală: mai întâi pe cei “plasați”, apoi pe cei “unplaced”
    return placed + unplaced



def solve_ga(rooms: List[Dict], surgeries: List[Dict], nurses: List[Dict], epoch: int = 500, pop: int = 80):
    n = len(surgeries)
    m = len(nurses)
    bounds = FloatVar(lb=[0.0] * (2 * n), ub=[1.0] * (2 * n), name="rk")

    def fitness(sol):
        raw_order = sorted(range(n), key=lambda i: sol[i])
        repaired_order = repair_chromosome_light(raw_order, surgeries, rooms)
        nurse_alloc = [int(sol[i + n] * m) for i in range(n)]
        _, cost = build_schedule(repaired_order, rooms, surgeries, nurse_alloc, nurses)
        return cost

    model = BaseGA(epoch=epoch, pop_size=pop, pc=0.9, pm=0.2)
    problem = {"obj_func": fitness, "bounds": bounds, "minmax": "min"}
    best = model.solve(problem)
    best_perm = sorted(range(n), key=lambda i: best.solution[i])
    nurse_alloc = [int(best.solution[i + n] * m) for i in range(n)]
    timetable, _ = build_schedule(best_perm, rooms, surgeries, nurse_alloc, nurses)
    
    

    return timetable



# =====================
# —— API PUBLIC ——
# =====================


def schedule_surgeries(selected_date: str):
    """
    Generează programul operațiilor pentru ziua aleasă.
    — rezervăm prin rotație una dintre cele 3 săli mari (is_large=True și laparoscopic=False)
      pentru cazurile de urgență;
    — sala de urgență apare cu un bloc „Rezervată pentru urgențe”,
      dar NU este folosită de algoritmul genetic.
    """
    # 0. date brute
    rooms, surgeries, nurses = fetch_data(selected_date)

    # 1. găsim prima sală mare
    # 1. identificăm primele 3 săli mari și alegem una în rotație în funcție de dată
    import datetime
    

    emergency_candidates = sorted(
        [r for r in rooms if r['is_large'] and not r['laparoscopic']],
        key=lambda x: x['id']
    )[:3]

    if emergency_candidates:
        date_obj = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
        idx = date_obj.toordinal() % len(emergency_candidates)
        emergency_room = emergency_candidates[idx]
    else:
        emergency_room = None

    # 2. lista pentru GA = toate sălile, mai puțin cea de urgențe (dacă există)
    if emergency_room:
        rooms_for_ga = [r for r in rooms if r["id"] != emergency_room["id"]]
    else:
        rooms_for_ga = rooms

    

    # 3. rulează optimizarea (doar pe sălile elective)
    if surgeries:
        timetable = solve_ga(rooms_for_ga, surgeries, nurses)
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
        timetable.sort(key=lambda x: (9999 if isinstance(x["room"], str) else int(x["room"])))

    
    

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