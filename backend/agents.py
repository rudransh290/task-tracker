"""
AI Task Tracker - Multi-Agent System
SDG 8: Decent Work and Economic Growth

Three agents work together:
1. Planner Agent   - breaks a project request into milestones
2. Task Agent      - breaks each milestone into concrete, assigned tasks
3. Reminder Agent  - drafts a reminder email for a task that is due/overdue
"""

import os
import json
from datetime import date, datetime
from typing import TypedDict, List

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
class TaskTrackerState(TypedDict):
    project_request: str
    employees: str
    current_timestamp: str
    milestones: List[dict]
    tasks: List[dict]


    def get_llm():
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
        reasoning_effort="low",
    )


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()
    return raw


# ---------------------------------------------------------------------------
# Agent 1: Planner Agent
# ---------------------------------------------------------------------------
def planner_agent(state: TaskTrackerState) -> TaskTrackerState:
    llm = get_llm()

    system_prompt = f"""You are a project planning agent. Your job is to break a project request into a clear, tight set of milestones and return them as structured data.

INPUTS:
- Project request: {state['project_request']}
- Current timestamp: {state['current_timestamp']}
- Available employees: {state['employees']}

TASK:
Decompose the project into 4 to 10 logical milestones. Each milestone is a meaningful phase or deliverable, not a tiny subtask. Order them so dependencies make sense. Build a sensible schedule starting from today unless the request specifies a start date. Assign exactly one owner per milestone from the available employees.

FIELD RULES:
Return a JSON list. Each milestone must have: milestone_name, description, owner, start_date, end_date, status, priority, progress.

CONSTRAINTS:
- Do not assign an owner who is not in available employees.
- Do not add commentary, explanation, or markdown.
- Return ONLY a valid JSON list, nothing else.
"""

    response = llm.invoke([SystemMessage(content=system_prompt)])
    raw = _clean_json(response.content)

    try:
        milestones = json.loads(raw)
    except json.JSONDecodeError:
        milestones = []

    state["milestones"] = milestones
    return state


# ---------------------------------------------------------------------------
# Agent 2: Task Agent
# ---------------------------------------------------------------------------
def task_agent(state: TaskTrackerState) -> TaskTrackerState:
    llm = get_llm()
    all_tasks = []

    for milestone in state["milestones"]:
        system_prompt = f"""You are a task generation agent. Given a single project milestone, you break it into concrete, actionable tasks and return them as structured data.

INPUTS:
- Milestone name: {milestone.get('milestone_name')}
- Description: {milestone.get('description')}
- Owner (default lead): {milestone.get('owner')}
- Priority: {milestone.get('priority')}
- Start date: {milestone.get('start_date')}
- End date: {milestone.get('end_date')}
- Current timestamp: {state['current_timestamp']}
- Available employees: {state['employees']}

TASK:
Break this milestone into 3 to 8 concrete tasks. Each task is a single piece of work someone can pick up and complete, not a vague theme. Order tasks logically. Keep every task's dates inside the milestone window. Assign each task to the most suitable person from available employees, matching their role and department to the work. The milestone owner is the default lead but delegate to others where their role fits better.

FIELD RULES:
Return a JSON list. Each task must have: task_name, description, assigned_to, department, priority, dependency_task_name, start_date, end_date, status, progress, estimated_hours, risk_level, next_action.

CONSTRAINTS:
- Assign only to people in available employees. Never invent a name.
- Do not add commentary or markdown.
- Return ONLY a valid JSON list, nothing else.
"""

        response = llm.invoke([SystemMessage(content=system_prompt)])
        raw = _clean_json(response.content)

        try:
            tasks = json.loads(raw)
            for t in tasks:
                t["milestone_name"] = milestone.get("milestone_name")
            all_tasks.extend(tasks)
        except json.JSONDecodeError:
            continue

    state["tasks"] = all_tasks
    return state


# ---------------------------------------------------------------------------
# Agent 3: Reminder Agent
# ---------------------------------------------------------------------------
def reminder_agent(task: dict) -> dict:
    llm = get_llm()

    system_prompt = f"""You are a task reminder agent. You write a short, professional reminder email to an employee about a task they have not yet completed. Your tone is polite, supportive, and clear.

INPUTS:
- Assignee name: {task.get('assigned_to')}
- Task name: {task.get('task_name')}
- Task description: {task.get('description')}
- Due date: {task.get('end_date')}
- Current date: {date.today().isoformat()}
- Priority: {task.get('priority', 'Medium')}
- Risk level: {task.get('risk_level', 'Low')}
- Next action: {task.get('next_action', '')}

TASK:
Write a reminder email. If due date equals current date, frame it as a friendly heads-up. If due date is before current date, mention it's overdue but stay courteous. Address the person by their first name. Mention the task and due date. Reference the next action. If priority is High/Critical or risk level is High, gently convey urgency without pressure. Invite them to reply with a status update. Close warmly, sign off as "The Project Team".

RULES:
- Keep the body under 130 words.
- Do not guilt-trip or use accusatory language.
- Return ONLY valid JSON with two keys: "subject" and "body". No markdown, no commentary.
"""

    response = llm.invoke([SystemMessage(content=system_prompt)])
    raw = _clean_json(response.content)

    try:
        email = json.loads(raw)
    except json.JSONDecodeError:
        email = {"subject": f"Reminder: {task.get('task_name')}", "body": raw}

    return email


# ---------------------------------------------------------------------------
# Build the graph (Planner -> Task Generator -> END)
# ---------------------------------------------------------------------------
def build_graph():
    builder = StateGraph(TaskTrackerState)
    builder.add_node("planner", planner_agent)
    builder.add_node("task_generator", task_agent)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "task_generator")
    builder.add_edge("task_generator", END)

    return builder.compile()


graph = build_graph()
