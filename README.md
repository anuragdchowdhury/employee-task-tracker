# Employee Weekly Task Tracker

A production-ready web application for employees to submit weekly tasks and for admins to manage employees and view submission reports.

Built with **Python FastAPI**, **MongoDB**, **Jinja2 Templates**, **Bootstrap 5**, and **Vanilla JavaScript**.

---

## Features

### Employee
- Login with username and password
- Submit weekly tasks (multiple tasks per submission)
- View submitted tasks (read-only after submission)
- One submission per week (Monday 00:00 – Sunday 23:59 IST)

### Admin
- Dashboard with weekly stats (total, submitted, pending)
- Create / Edit / Deactivate employee accounts
- Reset employee passwords
- View employee submission history
- View task details for any submission
- Generate WhatsApp summary report
- Copy report to clipboard

---

## Tech Stack

| Layer     | Technology                  |
|-----------|-----------------------------|
| Backend   | Python 3.12, FastAPI, Uvicorn |
| Templates | Jinja2                      |
| Frontend  | Bootstrap 5, Vanilla JS     |
| Database  | MongoDB 7                   |
| Auth      | bcrypt + signed cookies      |

---

## Quick Start with Docker

### Prerequisites
- Docker & Docker Compose installed

### 1. Clone the repository

```bash
cd emp-app
```

### 2. Configure environment variables

Edit `.env` as needed:

```env
MONGODB_URI=mongodb://mongo:27017
DATABASE_NAME=employee_task_tracker
SECRET_KEY=change-this-to-a-very-strong-secret-key-in-production
APP_NAME=Employee Weekly Task Tracker
```

### 3. Build and run

```bash
docker-compose up --build
```

The app will be available at: **http://localhost:8000**

---

## Default Admin Login

> ⚠️ **IMPORTANT**: Change the default admin password immediately after first login!

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

---

## Running Locally (without Docker)

### Prerequisites
- Python 3.12+
- MongoDB running on `localhost:27017`

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Update `.env`

```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=employee_task_tracker
SECRET_KEY=your-secret-key
APP_NAME=Employee Weekly Task Tracker
```

### 3. Run the app

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Project Structure

```
emp-app/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── database/
│   │   └── mongodb.py           # MongoDB connection & indexes
│   ├── models/
│   │   ├── employee.py          # Employee document factory
│   │   └── submission.py        # Submission document factory
│   ├── routes/
│   │   ├── auth.py              # Login / Logout routes
│   │   ├── employee.py          # Employee dashboard & task submission
│   │   └── admin.py             # Admin dashboard, CRUD, reports
│   ├── services/
│   │   ├── auth_service.py      # Auth, user CRUD, password management
│   │   └── submission_service.py# Submissions, dashboard, WhatsApp report
│   ├── utils/
│   │   ├── security.py          # bcrypt hashing, session tokens
│   │   └── timezone.py          # IST timezone, week calculation
│   ├── templates/
│   │   ├── base.html            # Base layout with sidebar
│   │   ├── login.html           # Login page
│   │   ├── employee/
│   │   │   └── dashboard.html   # Employee dashboard & task form
│   │   └── admin/
│   │       ├── dashboard.html   # Admin dashboard with stats
│   │       ├── employees.html   # Employee management list
│   │       ├── employee_form.html # Create/Edit employee form
│   │       ├── employee_history.html # Employee submission history
│   │       └── task_details.html # View task details
│   └── static/
│       ├── css/
│       │   └── style.css        # Custom styles
│       └── js/
│           └── app.js           # Client-side JavaScript
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── docker-compose.yml           # Docker Compose stack
└── README.md                    # This file
```

---

## MongoDB Setup

If running MongoDB manually:

```bash
# Using Docker
docker run -d --name mongodb -p 27017:27017 mongo:7

# Or install MongoDB locally
# See: https://www.mongodb.com/docs/manual/installation/
```

The application automatically creates required indexes on startup.

---

## Week Definition

| Start | Monday 00:00 IST  |
|-------|---------------------|
| End   | Sunday 23:59 IST    |

All times use the **Asia/Kolkata** timezone.

---

## Security Notes

- Passwords are hashed using **bcrypt**
- Sessions use **signed cookies** (itsdangerous)
- Admin routes are protected with role-based middleware
- Session tokens expire after **24 hours**

---

## License

MIT
