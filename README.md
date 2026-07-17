# TaskFlow AI — Multi-Agent Task Tracker

**SDG 8: Decent Work and Economic Growth**

An AI-powered project planning tool built with a three-agent pipeline using [LangGraph](https://github.com/langchain-ai/langgraph):

1. **Planner Agent** — breaks a project request into 4–10 logical milestones
2. **Task Agent** — breaks each milestone into 3–8 concrete tasks, assigned to the right teammate based on role/department
3. **Reminder Agent** — checks for due/overdue tasks and drafts polite reminder emails (can send real emails via Gmail SMTP)

---

## Project structure

```
task-tracker/
├── backend/
│   ├── main.py            FastAPI server (the API)
│   ├── agents.py          The three LangGraph agents
│   ├── employees.csv      Your team's data
│   ├── requirements.txt   Python dependencies
│   └── .env.example       Template for your API keys
├── frontend/
│   └── index.html         The web page (no build step needed)
└── README.md
```

---

## 1. Run it locally first (recommended before deploying)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste in your real GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

Your API is now running at `http://localhost:8000`. Check it works by visiting `http://localhost:8000/api/health` — you should see `{"status":"ok"}`.

### Frontend

Just open `frontend/index.html` directly in your browser (double-click it). It will talk to your local backend at `http://localhost:8000` automatically.

Try typing a project brief and clicking **Generate plan**.

---

## 2. Push to GitHub

```bash
cd task-tracker
git init
git add .
git commit -m "Initial commit: AI Task Tracker"
```

Create a new repository on [github.com](https://github.com), then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/task-tracker.git
git branch -M main
git push -u origin main
```

**Important:** the `.env` file (with your real API key) should never be pushed. Add a `.gitignore` file with:

```
.env
venv/
__pycache__/
tasks_store.json
```

---

## 3. Deploy the backend on Render (free)

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New → Web Service**
3. Select your `task-tracker` GitHub repo
4. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment**, add an environment variable:
   - `GROQ_API_KEY` = your real Groq key
   - (optional) `SMTP_EMAIL` and `SMTP_PASSWORD` if you want real emails sent
6. Click **Create Web Service**

Render will give you a live URL like `https://task-tracker-backend.onrender.com`. Test it by visiting `https://task-tracker-backend.onrender.com/api/health`.

---

## 4. Deploy the frontend on Vercel (free)

1. Open `frontend/index.html` and find this line near the bottom:
   ```js
   const API_BASE = window.API_BASE_URL || "http://localhost:8000";
   ```
   Change `"http://localhost:8000"` to your real Render URL, e.g.:
   ```js
   const API_BASE = window.API_BASE_URL || "https://task-tracker-backend.onrender.com";
   ```
2. Commit and push this change to GitHub
3. Go to [vercel.com](https://vercel.com), sign in with GitHub
4. Click **Add New → Project**, select your `task-tracker` repo
5. Set **Root Directory** to `frontend`
6. Framework Preset: choose **Other** (it's a plain static HTML site, no build needed)
7. Click **Deploy**

Vercel gives you a live URL like `https://task-tracker-yourteam.vercel.app` — this is the link you share in your submission PPT and put on GitHub/LinkedIn.

---

## 5. Sending real reminder emails (optional)

By default, the Reminder Agent only *drafts* emails (safe for demos — no accidental emails sent).

To make it send real emails via Gmail:

1. Go to your Google Account → Security → **2-Step Verification** (turn it on if not already)
2. Go to **App Passwords**, generate one for "Mail"
3. Set these environment variables (in `.env` locally, or in Render's environment settings):
   ```
   SMTP_EMAIL=youremail@gmail.com
   SMTP_PASSWORD=the_16_character_app_password
   ```

Once configured, clicking "Check reminders" will actually email the assigned employee.

---

## Notes for your submission

- Update `backend/employees.csv` with your real team's names, emails, and roles
- The team name, SDG, and problem statement are documented in the Lean Canvas
- Add screenshots of the working app + your live Vercel link to your pitch PPT
