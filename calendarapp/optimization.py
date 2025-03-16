import sqlite3
from mealpy.evolutionary_based.GA import BaseGA
from mealpy.utils.problem import FloatVar
from datetime import datetime

# Step 1: Fetch data from the database for a specific date
def fetch_data(selected_date):
    db_path = "db.sqlite3"
    
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Fetch rooms
    cursor.execute("""
        SELECT NrSala, SalaMare, Laparo, Chirurgie
        FROM website_sali
    """)
    rooms = cursor.fetchall()

    # -----------------------------------------------------------------
    # Modificat: preluăm din calendarapp_event
    # doar acele evenimente in_asteptare și data_interventie = selected_date
    # -----------------------------------------------------------------
    cursor.execute("""
        SELECT id,
               nume_pacient,
               tip_operatie,
               timp_estimare,
               data_interventie,
               user_id
        FROM calendarapp_event
        WHERE strftime('%Y-%m-%d', data_interventie) = ?
          AND status = 'in_asteptare'
    """, (selected_date,))
    surgeries = cursor.fetchall()

    connection.close()

    # Map data pentru săli
    # is_large = indică dacă sala e mare (SalaMare = True/False)
    # laparoscopic = indică dacă e echipată laparoscopic (Laparo = True/False)
    # surgery_type = ce tip de chirurgie poate găzdui, dacă ai astfel de informații.
    room_data = [
        {
            "id": r[0],
            "is_large": r[1],
            "laparoscopic": r[2],
            "surgery_type": r[3],  # opțional, după structura din website_sali
        }
        for r in rooms
    ]

    # Map data pentru evenimente
    # Observă că timp_estimare e deja integer => nu mai trebuie parsare HH:MM.
    surgery_data = [
        {
            "id": s[0],
            "name": s[1],     # echivalent nume_pacient
            "type": s[2],     # echivalent tip_operatie (ex. curata, murdara, laparoscopica)
            "duration": s[3], # direct integer (minute)
            "date": s[4],
            "surgeon": s[5],
        }
        for s in surgeries
    ]

    return room_data, surgery_data


# Step 2: Define constraints
def is_room_compatible(room, surgery):
    # 1) dacă intervenția e laparoscopica, sala trebuie să fie laparoscopic=True
    if surgery["type"] == "laparoscopica" and not room["laparoscopic"]:
        return False
    
    # 2) Poți adăuga alte condiții. Exemplu: dacă nu e sală mare, dar tipul e "clasica".
    # if not room["is_large"] and surgery["type"] == "clasica":
    #     return False
    
    return True

def calculate_cleaning_time(surgery):
    # timp de 10 minute dacă e "curata", 30 minute dacă e "murdara"
    if surgery["type"] == "curata":
        return 10
    elif surgery["type"] == "murdara":
        return 30
    # dacă e laparoscopica sau alt tip
    return 10  # sau alt timp default, după logica ta

def constraint_violations(solution, room_data, surgery_data):
    violations = 0
    room_schedules = [[] for _ in range(len(room_data))]

    # Map surgeries to rooms
    for surgery_idx, room_idx in enumerate(solution):
        room_schedules[int(round(room_idx))].append(surgery_idx)

    # Check room-specific constraints
    for room_idx, room_schedule in enumerate(room_schedules):
        if not room_schedule:
            continue

        last_end_time = 480  # Start at 8:00 AM (8 * 60)
        for surg_idx in room_schedule:
            surgery_info = surgery_data[surg_idx]
            room_info = room_data[room_idx]

            # Sala trebuie să fie compatibilă cu tipul intervenției
            if not is_room_compatible(room_info, surgery_info):
                violations += 1

            # Respect working hours: 8:00 - 17:00 => 8*60=480, 17*60=1020
            if last_end_time + surgery_info["duration"] > 1020:  # depășește 17:00
                violations += 1

            # Update end time (include și timpul de curățare)
            last_end_time += surgery_info["duration"] + calculate_cleaning_time(surgery_info)

    return violations


# Step 3: Fitness function
def fitness_function(solution, room_data, surgery_data):
    idle_time = 0
    cleanup_time = 0
    room_schedules = [[] for _ in range(len(room_data))]

    for surgery_idx, room_idx in enumerate(solution):
        room_schedules[int(round(room_idx))].append(surgery_idx)

    for room_schedule in room_schedules:
        if not room_schedule:
            continue

        last_end_time = 480  # 8:00 AM
        for surg_idx in room_schedule:
            surgery_info = surgery_data[surg_idx]

            # Idle time - exemplu de calcul
            # (depinde ce înțelegi prin idle_time; aici e lăsat minimal)
            # Se poate face un calcul mai complex dacă vrei să penalizezi pauzele
            idle_time += max(0, surgery_info["duration"] - (last_end_time - 480))

            # Timp total de curățare
            cleanup_time += calculate_cleaning_time(surgery_info)

            last_end_time += surgery_info["duration"] + calculate_cleaning_time(surgery_info)

    penalty = constraint_violations(solution, room_data, surgery_data)
    # Penalizare foarte mare pentru fiecare încălcare
    return idle_time + cleanup_time + penalty * 1000


# Step 4: Genetic algorithm to optimize scheduling
def schedule_surgeries(selected_date):
    room_data, surgery_data = fetch_data(selected_date)

    # Reserve the first room (index 0) as the emergency room - o lași dacă vrei să eviți Sala 0
    emergency_room_idx = 0

    # Definim bounds (float) exclusiv primei săli (dacă ai logica de a o omite)
    bounds = FloatVar(
        lb=[1] * len(surgery_data),  # start from room index 1
        ub=[len(room_data) - 1] * len(surgery_data),
        name="room_allocation"
    )

    def fitness(solution):
        return fitness_function(solution, room_data, surgery_data)

    model = BaseGA(epoch=500, pop_size=50, pc=0.9, pm=0.1)
    problem_dict = {"obj_func": fitness, "bounds": bounds, "minmax": "min"}
    best_agent = model.solve(problem_dict)

    # Construim un timetable (listă cu dicturi)
    rounded_solution = [int(round(x)) for x in best_agent.solution]
    timetable = []
    room_schedules = [[] for _ in range(len(room_data))]

    for surg_idx, room_idx in enumerate(rounded_solution):
        # ignorăm emergency_room_idx (dacă menții logica)
        if room_idx != emergency_room_idx:
            room_schedules[room_idx].append(surg_idx)

    for room_idx, surgeries in enumerate(room_schedules):
        room_timetable = {"room": room_data[room_idx]["id"], "schedule": []}
        last_end_time = 480  # 8:00 AM

        for s_idx in surgeries:
            surgery = surgery_data[s_idx]
            start_time = max(last_end_time, 480)
            end_time = start_time + surgery["duration"]

            room_timetable["schedule"].append({
                "surgery": surgery["name"],
                "start_time": f"{start_time // 60}:{start_time % 60:02d}",
                "end_time": f"{end_time // 60}:{end_time % 60:02d}"
            })
            # Actualizăm last_end_time
            last_end_time = end_time + calculate_cleaning_time(surgery)

        timetable.append(room_timetable)

    return timetable


# Main function to execute scheduling (test direct din consolă, dacă vrei)
if __name__ == "__main__":
    selected_date = input("Introduceți data pentru care doriți planificarea (YYYY-MM-DD): ")
    try:
        datetime.strptime(selected_date, '%Y-%m-%d')  # Validare format dată
        allocations = schedule_surgeries(selected_date)
        print("Planificare pentru data selectată:")
        for room in allocations:
            print(f"Sala {room['room']}:")
            for surgery in room["schedule"]:
                print(f"  {surgery['surgery']} - {surgery['start_time']} to {surgery['end_time']}")
    except ValueError:
        print("Formatul datei este invalid. Introduceți data în formatul YYYY-MM-DD.")
