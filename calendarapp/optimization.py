import sqlite3
from mealpy.evolutionary_based.GA import BaseGA
from mealpy.utils.problem import FloatVar
from datetime import datetime
import random


def fetch_data(selected_date):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT NrSala, SalaMare, Laparo, Chirurgie
        FROM website_sali
    """)
    rooms = cursor.fetchall()

    cursor.execute("""
        SELECT 
            e.id, 
            e.nume_pacient, 
            o.Nume, 
            e.timp_estimare, 
            e.data_interventie, 
            e.user_id,
            o.Laparoscopic, 
            o.OperatieCurata, 
            o.NecesitaIntubare
        FROM calendarapp_event e
        JOIN calendarapp_operatie o ON e.tip_operatie_id = o.id
        WHERE strftime('%Y-%m-%d', e.data_interventie) = ?
          AND e.status = 'in_asteptare'
    """, (selected_date,))
    surgeries = cursor.fetchall()

    connection.close()

    room_data = [
        {
            "id": r[0],
            "is_large": r[1],
            "laparoscopic": r[2],
            "chirurgie": r[3]
        }
        for r in rooms
    ]

    surgery_data = []
    for s in surgeries:
        surgery_data.append({
            "id": s[0],
            "name": s[1],
            "type": s[2],
            "duration": s[3],
            "date": s[4],
            "surgeon": s[5],
            "laparoscopic": s[6],
            "curata": s[7],
            "intubare": s[8]
        })

    return room_data, surgery_data


def calculate_cleaning_time(surgery):
    return 10 if surgery["curata"] else 30


def is_room_compatible(room, surgery):
    if surgery["intubare"] and room["id"] >= 10:
        return False
    if surgery["laparoscopic"] and not room["laparoscopic"]:
        return False
    return True


def constraint_violations(solution, room_data, surgery_data):
    violations = 0
    room_schedules = [[] for _ in range(len(room_data))]
    surgeon_schedules = {}
    sala_status = ["curata"] * len(room_data)

    for surgery_idx, room_idx in enumerate(solution):
        room_schedules[int(round(room_idx))].append(surgery_idx)

    for room_idx, room_schedule in enumerate(room_schedules):
        last_end_time = 480
        for surg_idx in room_schedule:
            surgery = surgery_data[surg_idx]
            room = room_data[room_idx]

            start_time = last_end_time
            end_time = start_time + surgery["duration"]

            if not is_room_compatible(room, surgery):
                violations += 1

            if end_time > 1020:
                violations += 1

            if sala_status[room_idx] == "murdara" and surgery["curata"]:
                violations += 1

            if not surgery["curata"]:
                sala_status[room_idx] = "murdara"

            surgeon = surgery["surgeon"]
            if surgeon not in surgeon_schedules:
                surgeon_schedules[surgeon] = []
            for scheduled_start, scheduled_end in surgeon_schedules[surgeon]:
                if not (end_time <= scheduled_start or start_time >= scheduled_end):
                    violations += 1
            surgeon_schedules[surgeon].append((start_time, end_time))

            last_end_time = end_time + calculate_cleaning_time(surgery)

    return violations


def fitness_function(solution, room_data, surgery_data):
    idle_time = 0
    cleanup_time = 0
    score_bonus = 0

    room_schedules = [[] for _ in range(len(room_data))]
    sala_status = ["curata"] * len(room_data)

    for surgery_idx, room_idx in enumerate(solution):
        room_schedules[int(round(room_idx))].append(surgery_idx)

    for room_idx, room_schedule in enumerate(room_schedules):
        last_end_time = 480
        for surg_idx in room_schedule:
            surgery = surgery_data[surg_idx]
            room = room_data[room_idx]

            start_time = last_end_time
            end_time = start_time + surgery["duration"]

            # Bonus logic
            if surgery["curata"]:
                score_bonus += 30
            if sala_status[room_idx] == "curata" and surgery["curata"]:
                score_bonus += 80
            if room["chirurgie"] == surgery["type"]:
                score_bonus += 40

            cleanup_time += calculate_cleaning_time(surgery)
            idle_time += max(0, surgery["duration"] - (last_end_time - 480))

            if not surgery["curata"]:
                sala_status[room_idx] = "murdara"

            last_end_time = end_time + calculate_cleaning_time(surgery)

    penalty = constraint_violations(solution, room_data, surgery_data)
    return idle_time + cleanup_time + penalty * 1000 - score_bonus


def schedule_surgeries(selected_date):
    room_data, surgery_data = fetch_data(selected_date)

    if not surgery_data:
        return []

    guard_room_idx = random.choice([0, 1, 2])  # alegem una din primele 3 săli

    bounds = FloatVar(
        lb=[0] * len(surgery_data),
        ub=[len(room_data) - 1] * len(surgery_data),
        name="room_allocation"
    )

    def fitness(sol):
        return fitness_function(sol, room_data, surgery_data)

    model = BaseGA(epoch=300, pop_size=50, pc=0.9, pm=0.1)
    problem_dict = {"obj_func": fitness, "bounds": bounds, "minmax": "min"}
    best_agent = model.solve(problem_dict)

    rounded_solution = [int(round(x)) for x in best_agent.solution]
    timetable = []
    room_schedules = [[] for _ in range(len(room_data))]

    for surg_idx, room_idx in enumerate(rounded_solution):
        if room_idx != guard_room_idx:
            room_schedules[room_idx].append(surg_idx)

    for room_idx, surgeries in enumerate(room_schedules):
        room_timetable = {"room": room_data[room_idx]["id"], "schedule": []}
        last_end_time = 480
        for s_idx in surgeries:
            surgery = surgery_data[s_idx]
            start_time = max(last_end_time, 480)
            end_time = start_time + surgery["duration"]
            room_timetable["schedule"].append({
                "id": surgery["id"],
                "surgery": surgery["name"],
                "start_time": f"{start_time // 60}:{start_time % 60:02d}",
                "end_time": f"{end_time // 60}:{end_time % 60:02d}",
                "surgeon": surgery["surgeon"]
            })
            last_end_time = end_time + calculate_cleaning_time(surgery)
        timetable.append(room_timetable)

    return timetable
