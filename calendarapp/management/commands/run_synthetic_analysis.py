import random
import itertools
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from django.core.management.base import BaseCommand
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


from calendarapp.optimization import build_schedule
from calendarapp.scenario_generator import (
    generate_synthetic_surgeries,
    generate_synthetic_rooms,
    generate_synthetic_nurses,
    generate_nurse_alloc
)

class Command(BaseCommand):
    help = "Rulează analiza sintetică și generează CSV + grafic."
    
    def is_feasible(self, surgeries: list[dict], rooms: list[dict], max_load: float = 0.95) -> bool:
        total_required = sum(s["duration"] + s["buffer"] for s in surgeries)
        total_available = len(rooms) * ((17 - 8) * 60)
        return total_required < total_available * max_load

    def handle(self, *args, **options):
        # 1. Configurare grilă de scenarii
        n_surgeries_list = [10, 20, 25, 30]
        pct_long_list    = [0.1, 0.2]
        n_rooms_list     = [10]
        n_nurses_list    = [11,13]
        n_surgeons_list  = [11,13,15]

        records = []
        for n, pct_long, rooms_n, nurses_n, surgeons_n in itertools.product(
        n_surgeries_list, pct_long_list, n_rooms_list, n_nurses_list, n_surgeons_list):


            # 2. Generează date sintetice
            rooms = generate_synthetic_rooms(rooms_n)
            surgeries = generate_synthetic_surgeries(n, pct_long, rooms, surgeons_n)

            nurses     = generate_synthetic_nurses(nurses_n)

            # 3. MULTI-START cu mai multe heuristici × semințe
            sorters = {
                "prio_dur_desc": lambda s: (s["priority"], s["duration"]),
                "dur_asc":       lambda s: s["duration"],
                "dur_desc":      lambda s: -s["duration"],
                "prio_desc":     lambda s: -s["priority"],
                "shuffle":       None,
                "prio_asc_dur_desc": lambda s: (s["priority"], -s["duration"]),
                "early_pref_first": lambda s: not s["early_pref"],
                "complex_first": lambda s: (s["complexity"], -s["priority"]),
                "early_window_first": lambda s: s["window_preference"] == "AM",

            }
            best_timetable, best_cost = None, None
            if not self.is_feasible(surgeries, rooms):
                self.stdout.write(self.style.WARNING(
                    f"[SKIPPED] {n} operații (long={pct_long}, nurses={nurses_n}) → overbooked"
                ))
                continue

            for name, key_fn in sorters.items():
                for seed in range(5):   # 5 seed-uri per heuristica
                    random.seed(seed)

                    # a) generează order conform fiecărei heuristici
                    if name == "shuffle":
                        order = list(range(len(surgeries)))
                        random.shuffle(order)
                    else:
                        order = sorted(
                            range(len(surgeries)),
                            key=lambda i: key_fn(surgeries[i]),
                            reverse=True
                        )

                    # b) regenerare aleatorie a alocării asistentelor
                    alloc = generate_nurse_alloc(n, nurses_n)

                    # c) apel la scheduler
                    tt, c = build_schedule(order, rooms, surgeries, alloc, nurses)

                    # d) reține cel mai bun
                    if best_cost is None or c < best_cost:
                        best_timetable, best_cost = tt, c

            # 4. Folosește cel mai bun rezultat
            timetable, cost = best_timetable, best_cost

            # 5. Calculează KPI-uri
            scheduled   = sum(
                1
                for room in timetable
                for ev in room.get("schedule", [])
                if not ev.get("unscheduled", False)
            )
            unscheduled = sum(
                1
                for room in timetable
                for ev in room.get("schedule", [])
                if ev.get("unscheduled", False)
            )
            total_used  = sum(room.get("total_used", 0) for room in timetable)
            total_slots = len(rooms) * (17 * 60 - 8 * 60)
            avg_util    = total_used / total_slots if total_slots else 0

            records.append({
                "n_surgeries": n,
                "n_surgeons": surgeons_n,
                "pct_long": pct_long,
                "n_rooms": rooms_n,
                "n_nurses": nurses_n,
                "scheduled": scheduled,
                "unscheduled": unscheduled,
                "avg_util_%": round(avg_util * 100, 1),
            })

        # 6. Salvează CSV-ul
        df = pd.DataFrame(records)
        out_csv = "synthetic_analysis.csv"
        df.to_csv(out_csv, index=False)
        self.stdout.write(self.style.SUCCESS(f"Rezultate salvate în {out_csv}"))
        self.stdout.write(str(df))

        # 7. Grafic: Operații neprogramate vs. săli pentru pct_long=0.2 și n_nurses=12
        sub = df[(df["pct_long"] == 0.2) & (df["n_nurses"] == 12)]
        for n in sorted(sub["n_surgeries"].unique()):
            part = sub[sub["n_surgeries"] == n]
            plt.plot(
                part["n_rooms"],
                part["unscheduled"],
                marker="o",
                label=f"n_surgeries={n}"
            )

        plt.xlabel("Număr săli")
        plt.ylabel("Operații neprogramate")
        plt.title("Neprogramate vs săli (pct_long=20%, nurses=12)")
        plt.legend()
        plt.tight_layout()
        plt.savefig("unscheduled_vs_rooms.png")
        
