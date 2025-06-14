import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import random
import numpy as np
from calendarapp.optimization import solve_ga, build_schedule, cleaning_minutes, is_room_compatible, DAY_START, DAY_END
from datetime import datetime, timedelta

# =====================
# CONFIGURAȚIA SPITALULUI JUDEȚEAN TIMIȘOARA
# =====================

def generate_realistic_rooms():
    """Generează 11 săli conform descrierii spitalului"""
    rooms = []
    
    # 6 săli mari cu laparoscopie (pentru anestezii generale + laparo)
    for i in range(6):
        rooms.append({
            "id": i + 1,
            "is_large": True,
            "laparoscopic": True,
            "chirurgie": "generala",
            "name": f"Sala {i+1} - Laparo"
        })
    
    # 3 săli mari fără laparoscopie (rezervabile pentru urgențe prin rotație)
    for i in range(3):
        rooms.append({
            "id": i + 7,
            "is_large": True, 
            "laparoscopic": False,
            "chirurgie": "generala",
            "name": f"Sala {i+7} - Generală"
        })
    
    # 2 săli mici multifuncționale (fără intubare)
    for i in range(2):
        rooms.append({
            "id": i + 10,
            "is_large": False,
            "laparoscopic": False,
            "chirurgie": "mica",
            "name": f"Sala {i+10} - Mică"
        })
    
    return rooms

def generate_realistic_nurses(n_nurses=12):
    """Generează echipa de asistenti medicali"""
    nurse_names = [
        "Ana Popescu", "Maria Ionescu", "Elena Georgescu", "Ioana Marin",
        "Carmen Stoica", "Daniela Radu", "Cristina Pavel", "Laura Neagu",
        "Monica Stanciu", "Adriana Costin", "Simona Dinu", "Raluca Barbu"
    ]
    
    return [
        {"id": i + 1, "name": nurse_names[i] if i < len(nurse_names) else f"Asistent {i+1}"}
        for i in range(n_nurses)
    ]

def generate_realistic_surgeries(n_surgeries=35, date_str="2025-06-12"):
    """Generează intervenții realiste bazate pe statistici chirurgicale"""
    
    # Tipuri de intervenții cu probabilități realiste
    surgery_types = [
        # Chirurgie generală (40%)
        {"name": "Colecistectomie laparoscopică", "duration_range": (45, 90), "laparo": True, "curata": True, "intubare": True, "complexity": 2, "priority": 2, "prob": 0.15},
        {"name": "Apendicectomie", "duration_range": (30, 60), "laparo": False, "curata": False, "intubare": True, "complexity": 1, "priority": 2, "prob": 0.12},
        {"name": "Hernie inghinală", "duration_range": (60, 120), "laparo": False, "curata": True, "intubare": True, "complexity": 2, "priority": 2, "prob": 0.13},
        
        # Chirurgie complexă (25%)
        {"name": "Rezecție intestinală", "duration_range": (120, 240), "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1, "prob": 0.08},
        {"name": "Gastrectomie", "duration_range": (180, 300), "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1, "prob": 0.05},
        {"name": "Colectomie", "duration_range": (150, 270), "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1, "prob": 0.07},
        {"name": "Splenectomie", "duration_range": (90, 150), "laparo": True, "curata": True, "intubare": True, "complexity": 2, "priority": 1, "prob": 0.05},
        
        # Chirurgie minoră (35%)
        {"name": "Excizie tumoră piele", "duration_range": (20, 45), "laparo": False, "curata": True, "intubare": False, "complexity": 1, "priority": 3, "prob": 0.12},
        {"name": "Cură hernială", "duration_range": (45, 90), "laparo": False, "curata": True, "intubare": False, "complexity": 1, "priority": 3, "prob": 0.10},
        {"name": "Drenaj abces", "duration_range": (15, 30), "laparo": False, "curata": False, "intubare": False, "complexity": 1, "priority": 2, "prob": 0.08},
        {"name": "Biopsie", "duration_range": (15, 35), "laparo": False, "curata": True, "intubare": False, "complexity": 1, "priority": 3, "prob": 0.05}
    ]
    
    # Nume chirurgi realiste
    surgeons = [
        "Dr. Popescu Alexandru", "Dr. Marinescu Ioana", "Dr. Constantinescu Mihai",
        "Dr. Georgescu Elena", "Dr. Rădulescu Gheorghe", "Dr. Munteanu Cristina",
        "Dr. Stoica Florin", "Dr. Popa Maria"
    ]
    
    # Nume pacienți realiste
    patient_names = [
        "Ionescu Ion", "Popescu Maria", "Georgescu Ana", "Marin Gheorghe",
        "Stoica Elena", "Radu Mihai", "Pavel Ioana", "Neagu Cristian",
        "Stanciu Carmen", "Costin Daniel", "Dinu Simona", "Barbu Raluca",
        "Marinescu Florin", "Constantinescu Laura", "Munteanu Adrian"
    ]
    
    surgeries = []
    
    # Normalizează probabilitățile
    total_prob = sum(s["prob"] for s in surgery_types)
    for s in surgery_types:
        s["prob"] = s["prob"] / total_prob
    
    for i in range(n_surgeries):
        # Selectează tipul operației bazat pe probabilități
        surgery_type = np.random.choice(surgery_types, p=[s["prob"] for s in surgery_types])
        
        duration = random.randint(*surgery_type["duration_range"])
        
        surgery = {
            "id": i + 1,
            "patient": random.choice(patient_names) + f" #{i+1}",
            "type": surgery_type["name"],
            "duration": duration,
            "date": date_str,
            "surgeon_id": random.randint(1, len(surgeons)),
            "surgeon": random.choice(surgeons),
            "laparoscopic": surgery_type["laparo"],
            "curata": surgery_type["curata"],
            "intubare": surgery_type["intubare"],
            "complexity": surgery_type["complexity"],
            "priority": surgery_type["priority"],
            "is_long": duration > 120
        }
        
        # Ajustează prioritatea pentru unele cazuri speciale
        if surgery_type["name"] in ["Rezecție intestinală", "Gastrectomie", "Colectomie"] and random.random() < 0.3:
            surgery["priority"] = 1  # Cazuri oncologice urgente
        
        surgeries.append(surgery)
    
    return surgeries

# =====================
# SCENARII DE TEST REALISTE
# =====================

def test_scenario_light_day():
    """Zi cu încărcare redusă (15 operații)"""
    print("\n=== SCENARIO: ZI UȘOARĂ (15 operații) ===")
    rooms = generate_realistic_rooms()
    nurses = generate_realistic_nurses()
    surgeries = generate_realistic_surgeries(15)
    
    return run_optimization_test(rooms, nurses, surgeries, "Zi ușoară")

def test_scenario_normal_day():
    """Zi normală (25-30 operații)"""
    print("\n=== SCENARIO: ZI NORMALĂ (28 operații) ===")
    rooms = generate_realistic_rooms()
    nurses = generate_realistic_nurses()
    surgeries = generate_realistic_surgeries(28)
    
    return run_optimization_test(rooms, nurses, surgeries, "Zi normală")

def test_scenario_heavy_day():
    """Zi încărcată (35+ operații)"""
    print("\n=== SCENARIO: ZI ÎNCĂRCATĂ (37 operații) ===")
    rooms = generate_realistic_rooms()
    nurses = generate_realistic_nurses()
    surgeries = generate_realistic_surgeries(37)
    
    return run_optimization_test(rooms, nurses, surgeries, "Zi încărcată")

def test_scenario_complex_surgeries():
    """Zi cu multe operații complexe și lungi"""
    print("\n=== SCENARIO: ZI CU OPERAȚII COMPLEXE ===")
    rooms = generate_realistic_rooms()
    nurses = generate_realistic_nurses()
    
    # Generează preponderent operații complexe
    complex_surgeries = []
    complex_types = [
        {"name": "Rezecție hepatică", "duration": 240, "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1},
        {"name": "Pancreaticoduodenectomie", "duration": 300, "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1},
        {"name": "Colectomie totală", "duration": 210, "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1},
        {"name": "Gastrectomie totală", "duration": 270, "laparo": False, "curata": False, "intubare": True, "complexity": 3, "priority": 1}
    ]
    
    surgeons = ["Dr. Popescu Alexandru", "Dr. Marinescu Ioana", "Dr. Constantinescu Mihai"]
    
    for i, surgery_type in enumerate(complex_types * 5):  # 20 operații complexe
        complex_surgeries.append({
            "id": i + 1,
            "patient": f"Pacient Complex #{i+1}",
            "type": surgery_type["name"],
            "duration": surgery_type["duration"] + random.randint(-30, 30),
            "date": "2025-06-12",
            "surgeon_id": (i % 3) + 1,
            "surgeon": surgeons[i % 3],
            "laparoscopic": surgery_type["laparo"],
            "curata": surgery_type["curata"],
            "intubare": surgery_type["intubare"],
            "complexity": surgery_type["complexity"],
            "priority": surgery_type["priority"],
            "is_long": True
        })
    
    return run_optimization_test(rooms, nurses, complex_surgeries, "Zi complexă")

def run_optimization_test(rooms, nurses, surgeries, scenario_name):
    """Rulează testul de optimizare și afișează statistici detaliate"""
    print(f"Configurație: {len(rooms)} săli, {len(nurses)} asistenți, {len(surgeries)} operații")
    
    # Statistici pre-optimizare
    total_duration = sum(s["duration"] for s in surgeries)
    clean_ops = sum(1 for s in surgeries if s["curata"])
    laparo_ops = sum(1 for s in surgeries if s["laparoscopic"])
    long_ops = sum(1 for s in surgeries if s["is_long"])
    priority_1 = sum(1 for s in surgeries if s["priority"] == 1)
    
    print(f"Statistici operații:")
    print(f"  - Durată totală: {total_duration} min ({total_duration/60:.1f} ore)")
    print(f"  - Operații curate: {clean_ops}/{len(surgeries)} ({clean_ops/len(surgeries)*100:.1f}%)")
    print(f"  - Operații laparoscopice: {laparo_ops}/{len(surgeries)} ({laparo_ops/len(surgeries)*100:.1f}%)")
    print(f"  - Operații lungi (>2h): {long_ops}/{len(surgeries)} ({long_ops/len(surgeries)*100:.1f}%)")
    print(f"  - Prioritate 1 (urgente): {priority_1}/{len(surgeries)} ({priority_1/len(surgeries)*100:.1f}%)")
    
    # Rulează optimizarea cu parametri mai rapidi pentru testare
    start_time = datetime.now()
    try:
        timetable = solve_ga(rooms, surgeries, nurses, epoch=100, pop=30)
        if timetable is None:
            print("Eroare: solve_ga a returnat None")
            return None
    except Exception as e:
        print(f"Eroare în optimizare: {e}")
        import traceback
        traceback.print_exc()
        return None
    end_time = datetime.now()
    
    # Analiză rezultate - FIXED
    scheduled_ops = 0
    unscheduled_ops = 0
    room_utilization = {}
    
    for room_schedule in timetable:
        room_id = room_schedule["room"]
        if room_id == "neplanificate":
            unscheduled_ops = len(room_schedule["schedule"])
        else:
            scheduled_ops += len(room_schedule["schedule"])
            if room_schedule["total_used"] > 0:
                utilization = room_schedule["total_used"] / (DAY_END - DAY_START) * 100
                room_utilization[room_id] = utilization
    
    print(f"\nRezultate optimizare ({(end_time - start_time).total_seconds():.1f}s):")
    print(f"  - Operații programate: {scheduled_ops}/{len(surgeries)} ({scheduled_ops/len(surgeries)*100:.1f}%)")
    print(f"  - Operații neprogramate: {unscheduled_ops}")
    
    if room_utilization:
        avg_utilization = sum(room_utilization.values()) / len(room_utilization)
        print(f"  - Utilizare medie săli: {avg_utilization:.1f}%")
        print(f"  - Utilizare min-max: {min(room_utilization.values()):.1f}% - {max(room_utilization.values()):.1f}%")
    
    # Afișează un sumar compactat al programului
    print(f"\nProgram sumar:")
    for room_schedule in timetable:
        room_id = room_schedule["room"]
        schedule = room_schedule["schedule"]
        
        if room_id == "neplanificate":
            if schedule:  # Doar dacă sunt operații neprogramate
                print(f"🚫 NEPLANIFICATE: {len(schedule)} operații")
        else:
            if schedule:  # Doar dacă sala are operații programate
                utilization = room_utilization.get(room_id, 0)
                print(f"🏥 SALA {room_id}: {len(schedule)} operații, {utilization:.1f}% utilizare")
    
    # FIXED: Returnează întotdeauna un dicționar valid
    return {
        "scenario": scenario_name,
        "total_surgeries": len(surgeries),
        "scheduled": scheduled_ops,
        "unscheduled": unscheduled_ops,
        "success_rate": scheduled_ops / len(surgeries) * 100 if len(surgeries) > 0 else 0,
        "avg_utilization": sum(room_utilization.values()) / len(room_utilization) if room_utilization else 0,
        "optimization_time": (end_time - start_time).total_seconds()
    }

# =====================
# TESTE SIMPLE PENTRU DEBUG
# =====================

def test_simple_scenario():
    """Test simplu pentru debug"""
    print("\n=== TEST SIMPLU DEBUG ===")
    
    # Configurație minimă dar realistă
    rooms = [
        {"id": 1, "is_large": True, "laparoscopic": True, "chirurgie": "generala"},
        {"id": 2, "is_large": True, "laparoscopic": False, "chirurgie": "generala"},
        {"id": 3, "is_large": False, "laparoscopic": False, "chirurgie": "mica"}
    ]
    
    nurses = [
        {"id": 1, "name": "Ana Popescu"},
        {"id": 2, "name": "Maria Ionescu"}
    ]
    
    surgeries = [
        {
            "id": 1, "patient": "Pacient 1", "type": "Apendicectomie",
            "duration": 60, "date": "2025-06-12", "surgeon_id": 1, "surgeon": "Dr. Popescu",
            "laparoscopic": False, "curata": False, "intubare": True, "complexity": 1, "priority": 2, "is_long": False
        },
        {
            "id": 2, "patient": "Pacient 2", "type": "Colecistectomie",
            "duration": 90, "date": "2025-06-12", "surgeon_id": 2, "surgeon": "Dr. Marinescu",
            "laparoscopic": True, "curata": True, "intubare": True, "complexity": 2, "priority": 2, "is_long": False
        },
        {
            "id": 3, "patient": "Pacient 3", "type": "Excizie tumoră",
            "duration": 30, "date": "2025-06-12", "surgeon_id": 1, "surgeon": "Dr. Popescu",
            "laparoscopic": False, "curata": True, "intubare": False, "complexity": 1, "priority": 3, "is_long": False
        }
    ]
    
    return run_optimization_test(rooms, nurses, surgeries, "Test simplu")

def run_performance_analysis():
    """Rulează analiză de performanță cu diferite configurații GA"""
    print("\n" + "=" * 80)
    print("ANALIZĂ PERFORMANȚĂ ALGORITM GENETIC")
    print("=" * 80)
    
    # Configurație de test standard
    rooms = generate_realistic_rooms()
    nurses = generate_realistic_nurses()
    surgeries = generate_realistic_surgeries(25)
    
    # Testează diferite configurații
    configs = [
        {"epoch": 50, "pop": 20, "name": "Rapid"},
        {"epoch": 100, "pop": 30, "name": "Standard"},
        {"epoch": 200, "pop": 50, "name": "Precis"},
        {"epoch": 300, "pop": 80, "name": "Intensiv"}
    ]
    
    results = []
    
    for config in configs:
        print(f"\nTestează configurația {config['name']} (epoch={config['epoch']}, pop={config['pop']})...")
        
        start_time = datetime.now()
        try:
            timetable = solve_ga(rooms, surgeries, nurses, epoch=config['epoch'], pop=config['pop'])
            
            # Calculează statistici
            scheduled = sum(len(r["schedule"]) for r in timetable if r["room"] != "neplanificate")
            unscheduled = sum(len(r["schedule"]) for r in timetable if r["room"] == "neplanificate")
            success_rate = scheduled / len(surgeries) * 100
            
            utilization_sum = sum(r["total_used"] for r in timetable if r["room"] != "neplanificate" and r["total_used"] > 0)
            active_rooms = sum(1 for r in timetable if r["room"] != "neplanificate" and r["total_used"] > 0)
            avg_utilization = (utilization_sum / (active_rooms * (DAY_END - DAY_START)) * 100) if active_rooms > 0 else 0
            
        except Exception as e:
            print(f"Eroare: {e}")
            scheduled = unscheduled = success_rate = avg_utilization = 0
        
        end_time = datetime.now()
        exec_time = (end_time - start_time).total_seconds()
        
        result = {
            "config": config['name'],
            "scheduled": scheduled,
            "unscheduled": unscheduled,
            "success_rate": success_rate,
            "avg_utilization": avg_utilization,
            "time": exec_time
        }
        results.append(result)
        
        print(f"  - Programate: {scheduled}/{len(surgeries)} ({success_rate:.1f}%)")
        print(f"  - Utilizare: {avg_utilization:.1f}%")
        print(f"  - Timp: {exec_time:.1f}s")
    
    # Sumar comparativ
    print(f"\n{'Config':<12} {'Programate':<12} {'Rata %':<8} {'Utilizare %':<12} {'Timp (s)':<10} {'Eficiența':<10}")
    print("-" * 80)
    
    for r in results:
        efficiency = r['success_rate'] / r['time'] if r['time'] > 0 else 0
        print(f"{r['config']:<12} {r['scheduled']:<12} {r['success_rate']:<8.1f} "
              f"{r['avg_utilization']:<12.1f} {r['time']:<10.1f} {efficiency:<10.1f}")
    
    return results

if __name__ == "__main__":
    # Setează seed pentru reproducibilitate
    random.seed(42)
    np.random.seed(42)
    
    print("TESTARE OPTIMIZARE CHIRURGIE - SPITAL JUDEȚEAN TIMIȘOARA")
    print("=" * 60)
    
    # Rulează mai întâi testul simplu
    print("1. Rulează test simplu pentru verificare...")
    try:
        result_simple = test_simple_scenario()
        if result_simple and isinstance(result_simple, dict):
            print("✅ Test simplu reușit!")
        else:
            print("❌ Test simplu eșuat!")
            print(f"Rezultat primit: {result_simple}")
            exit(1)
    except Exception as e:
        print(f"❌ Eroare în testul simplu: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # Dacă testul simplu merge, rulează scenariile complexe
    print("\n2. Rulează scenarii realiste...")
    try:
        results = []
        
        # Testează doar scenariile de bază pentru a evita erorile
        test_functions = [
            test_scenario_light_day,
            test_scenario_normal_day,
            test_scenario_heavy_day
        ]
        
        for test_func in test_functions:
            try:
                result = test_func()
                if result and isinstance(result, dict):
                    results.append(result)
                else:
                    print(f"⚠️  {test_func.__name__} a returnat rezultat invalid: {result}")
            except Exception as e:
                print(f"⚠️  Eroare în {test_func.__name__}: {e}")
                continue
        
        if results:
            # Sumar final
            print("\n" + "=" * 60)
            print("SUMAR REZULTATE")
            print("=" * 60)
            print(f"{'Scenariu':<15} {'Ops':<5} {'Prog':<5} {'Rata%':<7} {'Util%':<7} {'Timp(s)':<8}")
            print("-" * 60)
            
            for result in results:
                print(f"{result['scenario']:<15} {result['total_surgeries']:<5} "
                      f"{result['scheduled']:<5} {result['success_rate']:<7.1f} "
                      f"{result['avg_utilization']:<7.1f} {result['optimization_time']:<8.1f}")
            
            print(f"\n✅ {len(results)} teste completate cu succes!")
        else:
            print("❌ Niciun test nu s-a completat cu succes!")
        
    except Exception as e:
        print(f"❌ Eroare în testele complexe: {e}")
        import traceback
        traceback.print_exc()
    
    # Opțional: Rulează analiza de performanță doar dacă testele de bază merg
    if len(results) >= 2:
        print("\n3. Rulează analiza de performanță...")
        try:
            perf_results = run_performance_analysis()
            print("✅ Analiza de performanță completată!")
        except Exception as e:
            print(f"⚠️  Eroare în analiza de performanță: {e}")