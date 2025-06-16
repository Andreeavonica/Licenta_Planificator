# 🏥Si Intervențiilor Chirurgicale

Sistem informatic pentru planificarea interventiilor chirurgicale cu algoritmi genetici
---

## 💡 Ce face concret aplicația?

- Afișează un calendar cu operațiile planificate, în desfășurare și completate
- Folosește un algoritm genetic pentru a genera programări optime în funcție de:
  - durata intervențiilor
  - complexitate
  - priorități medicale
  - cerințe (sală mare, laparoscopică, intubare)
  - disponibilitatea personalului medical
-  Permite testarea pe date sintetice și analiza performanței algoritmului (KPI-uri), precum:
  -  Numărul total de operații programate vs. neprogramate
  -  Gradul de utilizare al sălilor
  -  Distribuția echilibrată a asistentelor
  -  Latența intervențiilor prioritare
  -  Penalizări pentru conflicte/întârzieri
-  Oferă actualizări în timp real prin WebSocket 

---

## 🧰 Tehnologii folosite

### Backend & Optimizare

| Tehnologie             | Rol                                                             |
|------------------------|------------------------------------------------------------------|
| **Python**             | Limbaj principal                                                 |
| **Django**             | Framework web (MVC, ORM, autentificare)                         |
| **Channels + Daphne**  | Suport WebSocket (ASGI)                                         |
| **SQLite**             | Bază de date local                                               |
| **mealpy**             | Algoritm genetic pentru optimizare                              |
| **Pandas**             | Prelucrare date                                                  |

###  Frontend (interfață)

| Tehnologie    | Rol                                                     |
|---------------|----------------------------------------------------------|
| **HTML5**     | Structură pagini                                         |
| **CSS3**      | Stilizare vizuală                                        |
| **Bootstrap** | Framework UI responsiv                                   |
| **JavaScript**| Funcționalități dinamice în interfață (ex: status live)  |

---

## Cum funcționează optimizarea?

Aplicația folosește un **algoritm genetic (GA)** pentru a genera un orar optimizat al intervențiilor chirurgicale.

Un GA simulează evoluția: începe cu soluții candidate (ordini de operații + alocări de personal), le evaluează printr-o funcție de cost și evoluează cele mai bune variante prin selecție, recombinare și mutație.

###  Ce ia în calcul:

-  Intervalul 08:00–17:00
-  Compatibilitatea sălii cu intervenția
-  Curățenia necesară între operații (curate/murdare)
-  Suprapuneri interzise între chirurgi și asistente
-  Penalizări pentru întârzieri la intervenții prioritare
-  Bonusuri pentru plasări bune (ex: devreme, curate, complexe)

---

## Instalare completă (pas cu pas)

### 1. Clonează proiectul

```bash
git clone https://github.com/utilizator/eventcalendar.git
cd eventcalendar
```

---

### 2. Creează și activează un mediu virtual

Pentru a izola dependențele proiectului și a evita conflictele cu alte aplicații Python, se folosește un mediu virtual (`venv`).

####  Pe Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Dacă folosești PowerShell și primești o eroare legată de permisiuni, rulează:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
venv\Scripts\activate
```

####  Pe Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Pentru a dezactiva mediul virtual ulterior:

```bash
deactivate
```

---

### 3. Instalează dependențele

```bash
pip install -r requirements.txt
```

Dacă lipsește `daphne`, rulează:

```bash
pip install daphne
```

---

### 4. Aplică migrațiile și creează un superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

 *Superuserul este necesar  pentru accesarea panoului de administrare (`/admin`).*

---

##  Rulare aplicație

###  Rulare simplă (fără WebSocket)

```bash
python manage.py runserver
```

> Recomandat pentru testare locală. WebSocket nu este activ.

---

###  Rulare completă cu WebSocket (Daphne)

```bash
daphne -b 0.0.0.0 -p 8000 eventcalendar.asgi:application
```

✔️ WebSocket activ (asigură-te că `channels`, `asgi.py` și `routing.py` sunt configurate – proiectul vine deja pregătit)

---
##  Generare și testare pe date sintetice

Aplicația permite testarea algoritmului de optimizare folosind date sintetice realiste, generate automat. Această funcționalitate este ideală pentru:

- validarea performanței algoritmului
- tuning-ul parametrilor
- analiza comportamentului în funcție de constrângeri și resurse

---
 Datele sintetice folosite pentru testare sunt create de scriptul:

```
calendarapp/scenario_generator.py
```

### Fișierul de comandă

Comanda este definită în fișierul:

```
calendarapp/management/commands/run_synthetic_analysis.py
```

---

###  Cum se rulează

Asigură-te că ești în directorul principal al proiectului și rulează:

```bash
python manage.py run_synthetic_analysis
```

---

###  Ce face această comandă?

-  Generează automat  scenarii sintetice, cu variații de:
  - durată și complexitate a intervențiilor
  - alocări de săli, chirurgi și asistente
-  Rulează algoritmul pe **mai multe seed-uri aleatoare** (de 5 ori per configurație)
-  Evaluează soluțiile și **selectează varianta cu costul cel mai mic**
-  Calculează automat **KPI-uri relevante** pentru fiecare scenariu:
  - Număr de operații programate vs. neprogramate
  - Gradul de ocupare a sălilor (în procente)
  - Conflict de personal (suprapuneri)
  - Timp pierdut cu intervenții prioritare întârziate
-  Salvează toate rezultatele într-un fișier `.csv`
-  Generează un grafic automat `.png` pentru comparație vizuală

---

###  Parametri de scenarii (configurați în script)

Poți modifica aceste liste din `run_synthetic_analysis.py` pentru a simula diverse situații reale:

```python
n_surgeries_list = [10, 20, 25, 30]     # număr de intervenții testate
pct_long_list    = [0.1, 0.2]           # proporția intervențiilor lungi/complexe
n_rooms_list     = [10]                 # număr de săli disponibile
n_nurses_list    = [11, 13]             # număr de asistente disponibile
n_surgeons_list  = [11, 13, 15]         # număr de chirurgi disponibili
```

 Modificarea acestor valori te ajută să înțelegi:

- Cât de bine scalează algoritmul
- Ce impact are lipsa de personal asupra programării
- Cum se comportă algoritmul în condiții stresate (resurse insuficiente)

---

###  Fișiere rezultate

| Fișier                     | Descriere                                                    |
|---------------------------|---------------------------------------------------------------|
| `synthetic_analysis.csv`  | Tabel cu toate scenariile testate și rezultatele aferente     |

---

 *Această analiză este ideală pentru cercetare operațională, proiecte academice sau demonstrarea performanței în medii clinice simulate.*


##  Testare unitară

Aplicația include teste unitare scrise folosind framework-ul `pytest`, împreună cu `pytest-django` pentru integrare cu Django.

### Cum rulezi testele

Asigură-te că ai instalat toate dependențele din `requirements.txt`, apoi execută:

```bash
pytest
```

✔️ Această comandă va căuta automat fișiere de test (ex: `test_*.py`) și va rula toate testele definite.

---

###  Recomandări:

- Rulează testele **din rădăcina proiectului** (acolo unde este `manage.py`)


###  Structura fișierelor de test

Toate testele se află în folderul:

```
calendarapp/tests
```


---

