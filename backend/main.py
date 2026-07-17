"""
FastAPI backend for the AI Task Tracker.

Endpoints:
- GET  /api/health         -> health check
- GET  /api/employees      -> list of team members
- POST /api/plan           -> run Planner + Task agents on a project request
- GET  /api/tasks          -> return the most recently generated tasks
- POST /api/remind         -> find due/overdue tasks and draft reminder emails
"""

import os
from dotenv import load_dotenv
load_dotenv()

import json
import smtplib
from datetime import date
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import graph, reminder_agent

BASE_DIR = Path(__file__).resolve().parent
EMPLOYEES_CSV = BASE_DIR / "employees.csv"
TASKS_STORE = BASE_DIR / "tasks_store.json"

app = FastAPI(title="AI Task Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_employees_df() -> pd.DataFrame:
    if not EMPLOYEES_CSV.exists():
        raise HTTPException(status_code=500, detail="employees.csv not found on server")
    return pd.read_csv(EMPLOYEES_CSV)


def load_tasks() -> list:
    if not TASKS_STORE.exists():
        return []
    with open(TASKS_STORE, "r") as f:
        return json.load(f)


def save_tasks(tasks: list) -> None:
    with open(TASKS_STORE, "w") as f:
        json.dump(tasks, f, indent=2)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a real email if SMTP credentials are configured, otherwise skip silently."""
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_email or not smtp_password or not to_email:
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_email
        msg["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, [to_email], msg.as_string())
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class PlanRequest(BaseModel):
    project_request: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/employees")
def get_employees():
    df = load_employees_df()
    return df.to_dict(orient="records")


@app.post("/api/plan")
def create_plan(payload: PlanRequest):
    df = load_employees_df()
    employees_string = str(df.to_dict(orient="records"))

    initial_state = {
        "project_request": payload.project_request,
        "employees": employees_string,
        "current_timestamp": datetime.now().isoformat(),
        "milestones": [],
        "tasks": [],
    }

    result = graph.invoke(initial_state)
    save_tasks(result["tasks"])

    return {
        "milestones": result["milestones"],
        "tasks": result["tasks"],
    }


@app.get("/api/tasks")
def get_tasks():
    return load_tasks()


@app.post("/api/remind")
def send_reminders():
    tasks = load_tasks()
    if not tasks:
        return {"due_count": 0, "reminders": []}

    df = load_employees_df()
    email_lookup = dict(zip(df["Employee_Name"], df["Email"]))

    today = date.today()
    reminders = []

    for task in tasks:
        try:
            end_date = date.fromisoformat(task.get("end_date", ""))
        except ValueError:
            continue

        if end_date <= today and str(task.get("status", "")).lower() != "completed":
            email = reminder_agent(task)
            to_email = email_lookup.get(task.get("assigned_to"), "")
            sent = send_email(to_email, email["subject"], email["body"])

            reminders.append({
                "assigned_to": task.get("assigned_to"),
                "email": to_email,
                "task_name": task.get("task_name"),
                "subject": email["subject"],
                "body": email["body"],
                "sent": sent,
            })

    return {"due_count": len(reminders), "reminders": reminders}
