# Manager Backend

REST API for event management, ticket reservations, and SAT Lista 69 data import.

---

## Architecture

```
manager-backend/
├── config/                       # Django project configuration
│   ├── settings/
│   │   ├── base.py               # Shared settings (DB, apps, DRF, CORS)
│   │   ├── development.py        # Dev overrides (DEBUG, verbose logging)
│   │   └── production.py         # Prod overrides (security headers)
│   ├── urls.py                   # Root router → /api/v1/
│   ├── wsgi.py
│   └── asgi.py
│
└── api/                          # Single Django app
    ├── models/
    │   ├── events/
    │   │   ├── event.py          # Event model
    │   │   └── reservation.py    # Reservation model (FK → Event)
    │   └── sat/
    │       ├── import_batch.py   # Tracks each SAT download execution
    │       └── canceled_taxpayer.py  # Individual records from Lista 69
    │
    ├── routes/
    │   ├── events.py             # EventViewSet + ReservationViewSet + urlpatterns
    │   └── sat.py                # SATImportBatchViewSet + CanceledTaxpayerViewSet + urlpatterns
    │
    ├── serializers/
    │   ├── event_serializers.py  # Event and Reservation validation + serialization
    │   └── sat_serializers.py    # SAT serialization
    │
    ├── services/
    │   ├── event_service.py      # Delete guard (checks existing reservations)
    │   ├── reservation_service.py  # Atomic spot deduction with SELECT FOR UPDATE
    │   └── sat_scraper.py        # Download → parse → bulk_create pipeline
    │
    └── admin.py                  # Django admin registrations
```

### Layer responsibilities

| Layer | Responsibility |
|---|---|
| **routes/** | ViewSets, URL routing, HTTP request/response |
| **serializers/** | Input validation, field-level constraints, data shaping |
| **services/** | Business operations: atomicity, external HTTP calls, bulk inserts |
| **models/** | ORM schema, DB constraints |

---

## Stack

| Tech | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| Django | 5.0.4 | Web framework |
| Django REST Framework | 3.15 | REST API |
| PostgreSQL | 16 | Database |
| docker-compose | - | Orchestration |
| requests + BeautifulSoup4 | - | SAT scraper |
| gunicorn | 22 | WSGI server |

> **Note on database:** Requirements mention SQL Express. PostgreSQL was chosen for better Django integration and simpler Docker setup. To use MSSQL, swap `psycopg2-binary` for `mssql-django` and update `DATABASES['ENGINE']` to `mssql`.

---

## Setup & Run

### Prerequisites
- Docker Desktop running

### Steps

```bash
# 1. Clone and enter the directory
git clone <repo-url>
cd manager-backend

# 2. Copy environment file
cp .env.example .env

# 3. Start services
docker-compose up --build
```

Runs migrations automatically and starts the API at `http://localhost:8000`.

### Create admin user (optional)

```bash
docker-compose exec backend python manage.py createsuperuser
```

### Run without Docker

> Requires Python 3.12 and a running PostgreSQL instance.

**Create and activate the virtual environment:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**Install dependencies, configure env and run:**

```bash
pip install -r requirements.txt
cp .env.example .env        # then set DB_HOST=localhost in .env
python manage.py makemigrations api
python manage.py migrate
python manage.py runserver
```

To deactivate the virtual environment when done:

```bash
deactivate
```

---

## API Endpoints

### Events  `/api/v1/events/`
| Method | URL | Action |
|---|---|---|
| GET | `/api/v1/events/` | List all events |
| POST | `/api/v1/events/` | Create event |
| GET | `/api/v1/events/{id}/` | Get event |
| PUT/PATCH | `/api/v1/events/{id}/` | Update event |
| DELETE | `/api/v1/events/{id}/` | Delete event |

Validations: `event_code` regex `^EVT-\d{4}-[A-Z]{2}$`, future date, name 5–100 chars, capacity > 0, price ≥ 0.

### Reservations  `/api/v1/reservations/`
| Method | URL | Action |
|---|---|---|
| GET | `/api/v1/reservations/` | List reservations |
| POST | `/api/v1/reservations/` | Create reservation |

Validations: valid email, `ticket_count` 1–5, available spots checked atomically.

### SAT Lista 69  `/api/v1/sat/`
| Method | URL | Action |
|---|---|---|
| POST | `/api/v1/sat/batches/trigger/` | Trigger SAT download and import |
| GET | `/api/v1/sat/batches/` | List import history |
| GET | `/api/v1/sat/canceled/` | List imported records |

---

## Health check

```
GET http://localhost:8000/health/
→ {"status": "ok", "service": "manager-backend"}
```

## Admin

`http://localhost:8000/admin/`
