# Enterprise Budget Management System — Django Backend

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env

# 3. Run migrations
python manage.py migrate

# 4. Seed initial data (optional)
python manage.py loaddata seed   # OR run the shell commands in SEED.md

# 5. Create superuser
python manage.py createsuperuser

# 6. Start server
python manage.py runserver
```

## Swagger UI
Open: http://127.0.0.1:8000/swagger/

## API Base URL
http://127.0.0.1:8000/api/

---

## Test Credentials (seed data)

| Username   | Password       | Role         |
|------------|----------------|--------------|
| admin      | Admin@1234     | admin        |
| manager1   | Manager@1234   | manager      |
| employee1  | Employee@1234  | employee     |
| finance1   | Finance@1234   | finance      |

---

## Module 1 — Auth Endpoints (`/api/auth/`)

| Method | URL                     | Description              |
|--------|-------------------------|--------------------------|
| POST   | /register/              | Register new user        |
| POST   | /login/                 | Get JWT token            |
| POST   | /token/refresh/         | Refresh access token     |
| GET    | /me/                    | My profile               |
| PATCH  | /me/                    | Update my profile        |
| GET    | /users/                 | List all users           |

## Module 2 — Budget Planning (`/api/budget-planning/`)

### Budget Cycles
| Method | URL              | Description              |
|--------|------------------|--------------------------|
| GET    | /cycles/         | List cycles              |
| POST   | /cycles/         | Create cycle             |
| GET    | /cycles/{id}/    | Get cycle detail         |
| PATCH  | /cycles/{id}/    | Update cycle             |
| DELETE | /cycles/{id}/    | Delete cycle             |

### Budget Categories
| Method | URL                  | Description          |
|--------|----------------------|----------------------|
| GET    | /categories/         | List categories      |
| POST   | /categories/         | Create category      |
| GET    | /categories/{id}/    | Get category         |
| PATCH  | /categories/{id}/    | Update category      |

### Budgets
| Method | URL                        | Description                  |
|--------|----------------------------|------------------------------|
| GET    | /                          | List budgets (with filters)  |
| POST   | /                          | Create budget                |
| GET    | /{id}/                     | Full budget detail           |
| PATCH  | /{id}/                     | Update budget                |
| DELETE | /{id}/                     | Delete budget                |
| PATCH  | /{id}/status/              | Change status                |
| POST   | /{id}/revise/              | Revise planned amount        |
| GET    | /{id}/revisions/           | Audit trail                  |
| GET    | /{id}/line-items/          | Budget line items            |
| POST   | /{id}/line-items/          | Add line item                |
| GET    | /overview/                 | Dashboard summary            |

---

## Postman Quick Test Flow

1. **Register** → POST `/api/auth/register/`
2. **Login** → POST `/api/auth/login/` → copy `access` token
3. **Set header** → `Authorization: Bearer <token>`
4. **Create Cycle** → POST `/api/budget-planning/cycles/`
5. **Create Budget** → POST `/api/budget-planning/`
6. **Activate Budget** → PATCH `/api/budget-planning/{id}/status/` `{"status": "active"}`
7. **Check Dashboard** → GET `/api/budget-planning/overview/`

---

## Budget Status Flow

```
draft → pending → approved → active → closed
                ↘ rejected
```

---

## Project Structure

```
budget_system/
├── core/               # Django project settings, URLs
├── accounts/           # Custom User model, JWT auth
├── budget_planning/    # Module 1: Budget Planning
│   ├── models.py       # BudgetCycle, BudgetCategory, Budget, BudgetLineItem, BudgetRevision
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── manage.py
├── requirements.txt
└── .env.example
```

## Coming Next Modules
- `spend_origin` — PO-based & employee expense tracking
- `reimbursement` — Expense claim + approval workflow
- `cost_control` — Budget validation & overrun detection
- `monitoring` — Analytics & dashboard aggregations
