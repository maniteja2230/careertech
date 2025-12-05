import os
from werkzeug.security import generate_password_hash, check_password_hash

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    url_for,
)
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from groq import Groq

# -------------------- FLASK CONFIG --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careertech_super_secret")

# -------------------- DB SETUP --------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careertech.db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)

Base = declarative_base()


def get_db():
    return SessionLocal()


@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


# -------------------- MODELS --------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    branch = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), nullable=False)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)  # Beginner / Intermediate / Advanced
    content = Column(Text, nullable=False)


class ProjectIdea(Base):
    __tablename__ = "project_ideas"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    difficulty = Column(String(50), nullable=False)  # Easy / Medium / Hard
    description = Column(Text, nullable=False)


class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True)
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    stipend = Column(String(100), nullable=False)
    remote = Column(Boolean, nullable=False, default=False)
    preferred_branches = Column(String(255), nullable=True)


class AiUsage(Base):
    """
    Tracks if a user has already used free AI roadmap chat.
    One row per user_id.
    """
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    ai_used = Column(Integer, nullable=False, default=0)


class Subscription(Base):
    """
    Simple subscription flag for each user.
    """
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=False)


# -------------------- DB INIT & SEED --------------------
def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    # Seed branches
    if db.query(Branch).count() == 0:
        branches = [
            ("Computer Science & Engineering", "CSE"),
            ("Information Technology", "IT"),
            ("Electronics & Communication", "ECE"),
            ("Electrical & Electronics", "EEE"),
            ("Mechanical Engineering", "ME"),
            ("Civil Engineering", "CE"),
            ("AI & Data Science", "AIDS"),
            ("Cyber Security", "CYBER"),
        ]
        for name, short in branches:
            db.add(Branch(name=name, short_name=short))

    # Seed sample roadmaps
    if db.query(Roadmap).count() == 0:
        # For simplicity, use small IDs (we know they start from 1)
        sample_roadmaps = [
            (1, "CSE – 1st & 2nd Year Roadmap (Foundations)", "Beginner",
             "• C basics → C++/Java\n• Python fundamentals\n• Data Structures & Algorithms\n• Git, GitHub basics\n• 1–2 simple projects"),
            (1, "CSE – 3rd & 4th Year Roadmap (Placements)", "Intermediate",
             "• Advanced DSA (LeetCode patterns)\n• DBMS, OS, CN revision\n• Web dev / backend specialization\n• 3–4 real-world projects\n• Mock interviews & contests"),
            (7, "AI & DS – Machine Learning Track", "Intermediate",
             "• Python + NumPy + Pandas\n• ML algorithms (regression, classification)\n• Mini projects on Kaggle datasets\n• Intro to Deep Learning\n• Resume-ready ML projects"),
        ]
        for branch_id, title, level, content in sample_roadmaps:
            db.add(Roadmap(branch_id=branch_id, title=title, level=level, content=content))

    # Seed sample project ideas
    if db.query(ProjectIdea).count() == 0:
        sample_projects = [
            (1, "Smart Career Recommendation System for Engineers", "Medium",
             "Use student skills, CGPA and interests to recommend suitable IT roles using ML."),
            (7, "Placement Predictor using ML", "Medium",
             "Predict chances of getting placed based on skills, projects, CGPA and contests."),
            (3, "IoT-Based Smart Energy Meter", "Hard",
             "Real-time energy monitoring with mobile dashboard using ESP32."),
        ]
        for b_id, title, diff, desc in sample_projects:
            db.add(ProjectIdea(branch_id=b_id, title=title, difficulty=diff, description=desc))

    # Seed sample internships
    if db.query(Internship).count() == 0:
        internships = [
            ("CareerTech Labs", "Full-Stack Developer Intern", "Remote", "₹8,000/month", True, "CSE, IT"),
            ("DataSphere Analytics", "Data Analyst Intern", "Hyderabad", "₹10,000/month", False, "CSE, AI & DS"),
            ("SecureNet Systems", "Cyber Security Intern", "Bengaluru", "₹12,000/month", False, "CSE, CYBER, IT"),
        ]
        for company, role, loc, stipend, remote, branches in internships:
            db.add(Internship(
                company=company,
                role=role,
                location=loc,
                stipend=stipend,
                remote=remote,
                preferred_branches=branches
            ))

    db.commit()
    db.close()


init_db()

# -------------------- GROQ AI HELPER --------------------
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


AI_SYSTEM_PROMPT = """
You are CareerTech, an AI mentor for B-Tech students in India.

Goal:
- Help students from branches like CSE, IT, ECE, EEE, Mechanical, Civil, AI & DS, Cyber, etc.
- Build a clear roadmap with: skills, projects, internships, and ideal roles.
- Match them with features similar to the CareerTech platform.

Ask step by step (not all at once):
1) Name, college year, and branch.
2) Current CGPA / percentage (rough is okay).
3) What they are interested in (e.g., web dev, AI, core jobs, higher studies, abroad, etc.).
4) How much time per day they can study.
5) If they want product-based, service-based, startup, or government jobs.
6) Whether they are open to internships and remote work.

Then:
- Suggest a clear roadmap (phases of 3–6 months).
- Recommend 2–4 project ideas aligned with their branch and goal.
- Suggest types of internships and companies to target.
- Keep language simple, structured, and motivating.

Very important:
- Do NOT mention that you are an AI model.
- At the end, say:

"To turn this plan into a live dashboard, CareerTech can show branch roadmaps, project bank and internship listings in one place."
"""

# -------------------- SUBSCRIPTION HELPER --------------------
def user_is_subscribed(user_id):
    if not user_id:
        return False
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    db.close()
    return bool(sub and sub.active)


# -------------------- BASE HTML LAYOUT (with AI Popup) --------------------
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% if title %}{{ title }}{% else %}CareerTech{% endif %}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/static/style.css">
  <style>
    .ai-fab {
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 1000;
    }
    .ai-modal-bg {
      position: fixed;
      inset: 0;
      background: rgba(2,6,23,0.6);
      display: none;
      z-index: 1000;
    }
    .ai-modal {
      position: fixed;
      right: 24px;
      bottom: 110px;
      width: 380px;
      max-width: 95%;
      background: #020617;
      border-radius: 18px;
      box-shadow: 0 18px 40px rgba(15,23,42,0.9);
      padding: 14px 16px 18px;
      display: none;
      z-index: 1001;
      border: 1px solid rgba(129,140,248,0.6);
    }
  </style>
</head>
<body class="bg-[#020617] text-white">

<div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">

  <!-- NAVBAR -->
  <nav class="flex justify-between items-center px-6 md:px-10 py-4 bg-black/40 backdrop-blur-md border-b border-slate-800">
    <!-- LOGO + TITLE -->
    <div class="flex items-center gap-3">
      <div class="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center shadow-lg shadow-indigo-500/40 overflow-hidden">
        <img src="/static/logo.png" class="w-11 h-11 object-contain" alt="CareerTech logo">
      </div>
      <div>
        <p class="font-bold text-lg md:text-xl tracking-tight">CareerTech</p>
        <p class="text-[11px] text-slate-400">B-Tech Careers · Skills · Internships</p>
      </div>
    </div>

    <!-- NAV LINKS -->
    <div class="hidden md:flex items-center gap-6 text-sm">
      <a href="/" class="hover:text-indigo-400">Home</a>
      <a href="/courses" class="hover:text-indigo-400">Courses</a>
      <a href="/colleges" class="hover:text-indigo-400">Colleges</a>
      <a href="/mentorship" class="hover:text-indigo-400">Mentorship</a>
      <a href="/jobs" class="hover:text-indigo-400">Jobs</a>
      <a href="/global-match" class="hover:text-indigo-400">Global Match</a>
      <a href="/chatbot" class="hover:text-indigo-400">AI Career Bot</a>
      <a href="/support" class="hover:text-indigo-400">Support</a>

      {% if session.get('user') %}
        <!-- user profile pill -->
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-700">
          <div class="w-7 h-7 rounded-full bg-indigo-500/80 flex items-center justify-center text-xs">
            {{ session.get('user')[0]|upper }}
          </div>
          <div class="flex flex-col leading-tight">
            <span class="text-[11px] text-slate-400">Logged in as</span>
            <span class="text-[13px] font-semibold">{{ session.get('user') }}</span>
          </div>
        </div>
        <a href="/logout" class="px-4 py-1.5 rounded-full bg-rose-500 hover:bg-rose-600 text-xs font-semibold shadow shadow-rose-500/40">
          Logout
        </a>
      {% else %}
        <a href="/login" class="px-4 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-xs font-semibold shadow shadow-indigo-500/40">
          Login
        </a>
      {% endif %}
    </div>
  </nav>

  <!-- PAGE CONTENT -->
  <main class="px-5 md:px-10 py-8">
    {{ content|safe }}
  </main>

</div>

<!-- AI pop-up FAB (chef bot) -->
<button id="aiFab" class="ai-fab bg-indigo-500 hover:bg-indigo-400 px-5 py-3 rounded-full shadow-xl flex items-center gap-2 text-sm md:text-base">
  <span class="text-2xl">👨‍🍳</span>
  <div class="hidden md:block text-left">
    <p class="text-[11px] text-slate-200 leading-none">Need help?</p>
    <p class="text-xs font-semibold leading-tight">Ask CareerTech AI</p>
  </div>
</button>

<!-- modal overlay -->
<div id="aiModalBg" class="ai-modal-bg"></div>

<!-- modal box -->
<div id="aiModal" class="ai-modal">
  <div class="flex items-center justify-between mb-2">
    <div>
      <p class="text-xs text-emerald-300 uppercase tracking-[0.18em]">CareerTech AI</p>
      <p class="text-sm font-semibold">Instant mentor for B-Tech</p>
    </div>
    <button id="closeAi" class="text-slate-400 hover:text-white text-lg leading-none">✕</button>
  </div>
  <p class="text-xs text-slate-300 mb-3">
    Ask doubts on branches, skills, projects, internships or let the AI take your mock interview.
  </p>
  <div class="flex flex-col gap-2">
    <a href="/chatbot" class="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs md:text-sm text-center">
      🚀 Start AI Career Chat
    </a>
    <a href="/mock-interviews/ai" class="px-3 py-2 rounded-lg border border-slate-700 hover:bg-slate-900 text-xs md:text-sm text-center">
      🎤 AI Mock Interview
    </a>
  </div>
</div>

<script>
  const aiFab = document.getElementById('aiFab');
  const aiModal = document.getElementById('aiModal');
  const aiModalBg = document.getElementById('aiModalBg');
  const closeAi = document.getElementById('closeAi');

  function openAi() {
    aiModal.style.display = 'block';
    aiModalBg.style.display = 'block';
  }
  function closeAiModal() {
    aiModal.style.display = 'none';
    aiModalBg.style.display = 'none';
  }

  if (aiFab) aiFab.addEventListener('click', openAi);
  if (aiModalBg) aiModalBg.addEventListener('click', closeAiModal);
  if (closeAi) closeAi.addEventListener('click', closeAiModal);

  // small entrance animation
  window.addEventListener('load', () => {
    setTimeout(() => {
      aiFab.classList.add('animate-bounce');
      setTimeout(() => aiFab.classList.remove('animate-bounce'), 1200);
    }, 1200);
  });
</script>

</body>
</html>
"""



def render_page(content_html, title="CareerTech"):
    return render_template_string(BASE_HTML, content=content_html, title=title)


# -------------------- AUTH TEMPLATES --------------------
SIGNUP_FORM = """
<form method="POST" class="max-w-md mx-auto bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
  <h2 class="text-xl font-bold mb-1">Create CareerTech Account</h2>
  <p class="text-[11px] text-slate-400 mb-2">For B-Tech students & graduates.</p>
  <input name="name" placeholder="Full name" class="input-box" required>
  <input name="email" placeholder="Email" class="input-box" required>
  <input name="branch" placeholder="Branch (e.g., CSE)" class="input-box">
  <input name="year" type="number" min="1" max="4" placeholder="Year (1-4)" class="input-box">
  <input name="password" type="password" placeholder="Password" class="input-box" required>
  <button class="submit-btn">Signup</button>
  <p class="text-gray-400 mt-2 text-xs">Already registered? <a href="/login" class="text-indigo-400">Login</a></p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="max-w-md mx-auto bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
  <h2 class="text-xl font-bold mb-1">Login to CareerTech</h2>
  <p class="text-[11px] text-slate-400 mb-2">Access your dashboard, roadmaps & internships.</p>
  <input name="email" placeholder="Email" class="input-box" required>
  <input name="password" type="password" placeholder="Password" class="input-box" required>
  <button class="submit-btn">Login</button>
  <p class="text-gray-400 mt-2 text-xs">New here? <a href="/signup" class="text-indigo-400">Create account</a></p>
</form>
"""


# -------------------- AUTH ROUTES --------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        branch = request.form.get("branch", "").strip()
        year_raw = request.form.get("year", "").strip()

        if not name or not email or not password:
            return render_page(
                "<p class='text-red-400 text-xs mb-2 text-center'>All fields marked * are required.</p>" + SIGNUP_FORM,
                "Signup"
            )

        db = get_db()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.close()
            return render_page(
                "<p class='text-red-400 text-xs mb-2 text-center'>Account already exists. Please login.</p>" + SIGNUP_FORM,
                "Signup"
            )

        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None

        hashed_password = generate_password_hash(
            password,
            method="pbkdf2:sha256",
            salt_length=16
        )
        user = User(
            name=name,
            email=email,
            password=hashed_password,
            branch=branch,
            year=year,
        )
        db.add(user)
        db.commit()
        db.close()
        return redirect("/login")

    return render_page(SIGNUP_FORM, "Signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.query(User).filter(User.email == email).first()
        db.close()

        authenticated = False
        if user:
            try:
                authenticated = check_password_hash(user.password, password)
            except ValueError:
                authenticated = (user.password == password)

        if authenticated:
            session["user"] = user.name
            session["user_id"] = user.id
            session["first_time"] = True
            session["ai_history"] = []
            return redirect("/dashboard")

        return render_page(
            "<p class='text-red-400 text-xs mb-2 text-center'>Invalid email or password.</p>" + LOGIN_FORM,
            "Login"
        )

    return render_page(LOGIN_FORM, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------- HOME --------------------
@app.route("/")
def home():
    user_id = session.get("user_id")
    logged_in = bool(user_id)
    subscribed = user_is_subscribed(user_id)

    if logged_in:
        if subscribed:
            cta_html = """
              <div class="flex flex-wrap items-center gap-3 mt-3">
                <a href="/dashboard" class="primary-cta">
                  🚀 Go to your CareerTech dashboard
                </a>
                <a href="/internships" class="ghost-cta">
                  🔎 View internships
                </a>
              </div>
            """
        else:
            cta_html = """
              <div class="flex flex-wrap items-center gap-3 mt-3">
                <a href="/subscribe" class="primary-cta">
                  🔓 Unlock full access – ₹299 / year
                </a>
                <a href="/dashboard" class="ghost-cta">
                  View dashboard
                </a>
              </div>
            """
    else:
        cta_html = """
          <div class="flex flex-wrap items-center gap-3 mt-3">
            <a href="/signup" class="primary-cta">
              Create free CareerTech account
            </a>
            <a href="/login" class="ghost-cta">
              Login
            </a>
          </div>
          <p class="text-[11px] text-slate-400 mt-2">
            Start free. Upgrade later to unlock full roadmaps, internships & interview prep.
          </p>
        """

    content = f"""
    <div class="max-w-6xl mx-auto mt-4 md:mt-8 space-y-10">

      <!-- HERO -->
      <section class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-3">
          <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/40 text-[11px] text-emerald-300">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Built for B-Tech students
          </span>

          <h1 class="text-3xl md:text-4xl font-extrabold leading-tight">
            Plan your <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-cyan-300 to-emerald-300">tech career</span>
            from 1st year to dream job.
          </h1>

          <p class="text-xs md:text-sm text-slate-300">
            CareerTech is a 24/7 career platform for B-Tech students.
            It combines branch-wise roadmaps, project ideas, internships and AI mentorship in one dashboard.
          </p>

          {cta_html}

          <div class="grid grid-cols-3 gap-3 mt-5 text-[11px] text-slate-300">
            <div class="dash-box">
              <p class="text-slate-400 text-[10px]">Vision</p>
              <p class="font-semibold mt-1">India's strongest tech career ecosystem for engineering students.</p>
            </div>
            <div class="dash-box">
              <p class="text-slate-400 text-[10px]">Problem</p>
              <p class="mt-1">Lack of real skills, poor guidance, weak projects & zero internship clarity.</p>
            </div>
            <div class="dash-box">
              <p class="text-slate-400 text-[10px]">Solution</p>
              <p class="mt-1">One platform for skills, projects, internships, and global pathways.</p>
            </div>
          </div>
        </div>

        <div class="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4">
          <p class="text-xs text-slate-400 uppercase tracking-[0.22em]">Student pass</p>
          <div class="flex items-end gap-2">
            <span class="text-5xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-xs text-slate-300 mb-2">per student / year</span>
          </div>
          <p class="text-[11px] md:text-xs text-slate-300">
            Affordable access to branch roadmaps, project bank, internship listings and AI-powered guidance.
          </p>
          <ul class="text-[11px] text-slate-200 space-y-1 mt-1">
            <li>• Branch-wise skill & roadmap dashboard</li>
            <li>• Final-year project ideas with descriptions</li>
            <li>• Internship & fresher job snapshots</li>
            <li>• AI career roadmap mentor + mock interviews</li>
            <li>• Study-abroad and MS planning guidance (basic)</li>
          </ul>
        </div>
      </section>

      <!-- FEATURE GRID -->
      <section class="space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">CareerTech Spaces</h3>
        <div class="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <a href="/branches" class="feature-card">
            🧭 Branch Explorer
            <p class="text-[11px] text-slate-400 mt-1">See all supported branches and paths.</p>
          </a>
          <a href="/roadmaps" class="feature-card">
            🛣️ Roadmaps
            <p class="text-[11px] text-slate-400 mt-1">1st year to 4th year guidance.</p>
          </a>
          <a href="/projects" class="feature-card">
            💡 Projects
            <p class="text-[11px] text-slate-400 mt-1">Final-year & mini project ideas.</p>
          </a>
          <a href="/internships" class="feature-card">
            💼 Internships
            <p class="text-[11px] text-slate-400 mt-1">Sample tech internships & roles.</p>
          </a>
          <a href="/mock-interview" class="feature-card">
            🎤 Interview Bot
            <p class="text-[11px] text-slate-400 mt-1">Practice HR + technical rounds.</p>
          </a>
          <a href="/study-abroad" class="feature-card">
            🌍 Study Abroad
            <p class="text-[11px] text-slate-400 mt-1">MS & global opportunity overview.</p>
          </a>
        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerTech | Home")


# -------------------- SUBSCRIBE ROUTE --------------------
@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id).first()

    if request.method == "POST":
        if not sub:
            sub = Subscription(user_id=user_id, active=True)
            db.add(sub)
        else:
            sub.active = True
        db.commit()
        db.close()
        return redirect("/dashboard")

    db.close()
    content = """
    <div class="max-w-lg mx-auto bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
      <h2 class="text-2xl font-bold mb-1">Unlock CareerTech Student Pass</h2>
      <p class="text-xs text-slate-300">
        Subscription (demo) to unlock full access to roadmaps, project bank, internships and AI mock interviews.
      </p>
      <ul class="text-xs text-slate-200 space-y-1">
        <li>• Full branch-wise roadmaps</li>
        <li>• Detailed project descriptions</li>
        <li>• All internship snapshots</li>
        <li>• Unlimited AI mock interviews</li>
      </ul>
      <form method="POST" class="mt-3">
        <button class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold">
          Subscribe – ₹299 / year (demo)
        </button>
      </form>
    </div>
    """
    return render_page(content, "Subscribe")


# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user_name = session["user"]

    db = get_db()
    user = db.query(User).get(user_id)
    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    db.close()

    subscribed = bool(sub and sub.active)
    first_time = session.pop("first_time", False)

    greeting = "CareerTech welcomes you 🎉" if first_time else "Welcome back 👋"

    branch_label = user.branch or "Not set"
    year_label = f"{user.year} year" if user.year else "Not set"

    sub_status = "Active" if subscribed else "Free"

    content = f"""
    <div class="max-w-5xl mx-auto space-y-6">
      <div>
        <p class="text-xs text-slate-400">Dashboard · B-Tech student</p>
        <h1 class="text-2xl md:text-3xl font-bold">{greeting}, {user_name}</h1>
        <p class="text-xs text-slate-300 mt-1">
          Plan your entire B-Tech journey – from skills and projects to internships and global opportunities.
        </p>
      </div>

      <div class="grid md:grid-cols-3 gap-4">
        <div class="dash-box">
          <p class="text-[11px] text-slate-400">Branch</p>
          <p class="mt-1 text-sm font-semibold">{branch_label}</p>
        </div>
        <div class="dash-box">
          <p class="text-[11px] text-slate-400">Year</p>
          <p class="mt-1 text-sm font-semibold">{year_label}</p>
        </div>
        <div class="dash-box">
          <p class="text-[11px] text-slate-400">Plan type</p>
          <p class="mt-1 text-sm font-semibold">{sub_status}</p>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="dash-box">
          <h3 class="text-sm font-semibold mb-1">CareerTech guidance</h3>
          <ul class="text-[11px] text-slate-300 space-y-1">
            <li>• Start with your branch roadmap (1st–4th year plan).</li>
            <li>• Pick 2–3 solid projects before final year.</li>
            <li>• Apply for relevant internships from 2nd/3rd year.</li>
            <li>• Use the AI bot for roadmaps and interview practice.</li>
          </ul>
        </div>
        <div class="dash-box">
          <h3 class="text-sm font-semibold mb-1">How to use this platform</h3>
          <ol class="text-[11px] text-slate-300 space-y-1 list-decimal list-inside">
            <li>Open <b>Branches</b> & choose your branch.</li>
            <li>Check your <b>roadmap</b> and note skills to learn.</li>
            <li>Go to <b>Projects</b> and shortlist 1–2 ideas.</li>
            <li>Visit <b>Internships</b> to understand roles & stipends.</li>
            <li>Use <b>AI Career Bot</b> for a personalised plan.</li>
          </ol>
          <p class="mt-2 text-[10px] text-slate-500">
            (Demo video can be embedded here later using a real hosted link.)
          </p>
        </div>
      </div>

      <div class="grid md:grid-cols-3 gap-4">
        <a href="/roadmaps" class="dash-box hover:border-indigo-500 transition cursor-pointer">
          <h3 class="text-sm font-semibold mb-1">Roadmaps</h3>
          <p class="text-[11px] text-slate-300">See branch-wise skill and semester planning.</p>
        </a>
        <a href="/projects" class="dash-box hover:border-indigo-500 transition cursor-pointer">
          <h3 class="text-sm font-semibold mb-1">Project ideas</h3>
          <p class="text-[11px] text-slate-300">Browse mini and major ideas aligned to your goals.</p>
        </a>
        <a href="/internships" class="dash-box hover:border-indigo-500 transition cursor-pointer">
          <h3 class="text-sm font-semibold mb-1">Internships</h3>
          <p class="text-[11px] text-slate-300">View sample tech internships & stipend ranges.</p>
        </a>
      </div>
    </div>
    """
    return render_page(content, "Dashboard")


# -------------------- BRANCHES --------------------
@app.route("/branches")
def branches():
    db = get_db()
    data = db.query(Branch).order_by(Branch.name.asc()).all()
    db.close()

    cards = ""
    for b in data:
        cards += f"""
        <a href="/roadmaps?branch_id={b.id}" class="feature-card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold">{b.name}</p>
              <p class="text-[11px] text-slate-400 mt-0.5">Short: {b.short_name}</p>
            </div>
            <span class="text-slate-500 text-xs">View roadmap →</span>
          </div>
        </a>
        """

    content = f"""
    <h2 class="text-2xl md:text-3xl font-bold mb-3">Supported Branches</h2>
    <p class="text-xs text-slate-300 mb-3">
      CareerTech focuses on core B-Tech branches across software, electronics and core engineering.
    </p>
    <div class="grid md:grid-cols-3 gap-4">
      {cards}
    </div>
    """
    return render_page(content, "Branches | CareerTech")


# -------------------- ROADMAPS --------------------
@app.route("/roadmaps")
def roadmaps():
    branch_id = request.args.get("branch_id", "").strip()

    db = get_db()
    branches = db.query(Branch).order_by(Branch.name.asc()).all()

    selected_branch = None
    roadmap_query = db.query(Roadmap)
    if branch_id:
        try:
            bid = int(branch_id)
            selected_branch = db.query(Branch).get(bid)
            roadmap_query = roadmap_query.filter(Roadmap.branch_id == bid)
        except ValueError:
            pass

    roadmaps_data = roadmap_query.order_by(Roadmap.level.asc()).all()
    db.close()

    # branch dropdown
    options = '<option value="">All branches</option>'
    for b in branches:
        sel = "selected" if str(b.id) == branch_id else ""
        options += f"<option value='{b.id}' {sel}>{b.short_name} – {b.name}</option>"

    rows = ""
    for r in roadmaps_data:
        rows += f"""
        <div class="dash-box">
          <p class="text-[10px] text-slate-400 mb-1">{r.level}</p>
          <h3 class="text-sm font-semibold mb-1">{r.title}</h3>
          <pre class="whitespace-pre-wrap text-[11px] text-slate-300">{r.content}</pre>
        </div>
        """

    if not rows:
        rows = "<p class='text-xs text-slate-400'>No roadmap found yet for this branch.</p>"

    content = f"""
    <div class="max-w-5xl mx-auto space-y-4">
      <div class="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h2 class="text-2xl font-bold">Branch Roadmaps</h2>
          <p class="text-xs text-slate-300">
            High-level plans from foundations to placements. Use along with your college syllabus.
          </p>
        </div>
        <form method="GET" class="flex items-center gap-2">
          <select name="branch_id" class="input-box text-[11px]" onchange="this.form.submit()">
            {options}
          </select>
        </form>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        {rows}
      </div>
    </div>
    """
    return render_page(content, "Roadmaps | CareerTech")


# -------------------- PROJECTS --------------------
@app.route("/projects")
def projects():
    user_id = session.get("user_id")
    subscribed = user_is_subscribed(user_id)

    db = get_db()
    projects = db.query(ProjectIdea).all()
    db.close()

    cards = ""
    for idx, p in enumerate(projects):
        locked = (not subscribed and idx >= 2)  # show only first 2 fully on free tier
        if locked:
            desc_html = "<p class='text-[11px] text-slate-500 mt-1'>Subscribe to unlock full description.</p>"
        else:
            desc_html = f"<p class='text-[11px] text-slate-300 mt-1'>{p.description}</p>"

        overlay = ""
        if locked:
            overlay = """
              <div class="absolute inset-0 bg-slate-950/70 rounded-2xl flex flex-col items-center justify-center text-center">
                <p class="text-xs font-semibold mb-1">Locked content</p>
                <p class="text-[11px] text-slate-300 mb-2 px-4">Subscribe to view full project bank with detailed explanations.</p>
                <a href="/subscribe" class="px-3 py-1.5 rounded-full bg-indigo-600 text-[11px]">Unlock</a>
              </div>
            """

        cards += f"""
        <div class="relative dash-box overflow-hidden">
          <p class="text-[10px] text-slate-400 mb-1">Difficulty: {p.difficulty}</p>
          <h3 class="text-sm font-semibold">{p.title}</h3>
          {desc_html}
          {overlay}
        </div>
        """

    content = f"""
    <div class="max-w-5xl mx-auto space-y-4">
      <h2 class="text-2xl font-bold">Project Ideas</h2>
      <p class="text-xs text-slate-300">
        Pick 1–2 strong projects to showcase your skills. Focus more on execution quality than number of projects.
      </p>
      <div class="grid md:grid-cols-2 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Projects | CareerTech")


# -------------------- INTERNSHIPS --------------------
@app.route("/internships")
def internships():
    user_id = session.get("user_id")
    subscribed = user_is_subscribed(user_id)

    db = get_db()
    data = db.query(Internship).all()
    db.close()

    cards = ""
    for it in data:
        tag = "Remote" if it.remote else it.location
        blur_class = "" if subscribed else "blur-[2px] opacity-80"
        overlay = ""
        if not subscribed:
            overlay = """
              <div class="absolute inset-0 bg-slate-950/75 rounded-2xl flex flex-col items-center justify-center text-center">
                <p class="text-xs font-semibold mb-1">Subscribe to see full internship details</p>
                <a href="/subscribe" class="px-3 py-1.5 rounded-full bg-indigo-600 text-[11px]">Unlock internships</a>
              </div>
            """

        cards += f"""
        <div class="relative dash-box overflow-hidden">
          <div class="{blur_class}">
            <h3 class="text-sm font-semibold mb-1">{it.role}</h3>
            <p class="text-[11px] text-indigo-300 mb-1">{it.company}</p>
            <p class="text-[11px] text-slate-300">Location: {tag}</p>
            <p class="text-[11px] text-emerald-300 mt-1">Stipend: {it.stipend}</p>
            <p class="text-[10px] text-slate-400 mt-1">Preferred branches: {it.preferred_branches}</p>
          </div>
          {overlay}
        </div>
        """

    content = f"""
    <div class="max-w-5xl mx-auto space-y-4">
      <h2 class="text-2xl font-bold">Internships & Roles</h2>
      <p class="text-xs text-slate-300 mb-2">
        These are sample roles showing the type of internships you can target as a B-Tech student.
        Real listings will come from partnered companies and job portals.
      </p>
      <div class="grid md:grid-cols-3 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Internships | CareerTech")


# -------------------- STUDY ABROAD --------------------
@app.route("/study-abroad")
def study_abroad():
    content = """
    <div class="max-w-5xl mx-auto space-y-4">
      <h2 class="text-2xl font-bold">Study Abroad Centre</h2>
      <p class="text-xs text-slate-300">
        Many engineering students plan for MS abroad in CS, Data, Robotics, VLSI and other domains.
        This section gives a high-level idea only.
      </p>
      <div class="grid md:grid-cols-3 gap-4">
        <div class="dash-box">
          <h3 class="text-sm font-semibold mb-1">Popular destinations</h3>
          <ul class="text-[11px] text-slate-300 space-y-1">
            <li>• USA – MS in CS, DS, AI</li>
            <li>• Germany – low tuition, strong engineering</li>
            <li>• Canada – PR-friendly, tech jobs</li>
            <li>• UK – 1-year masters</li>
          </ul>
        </div>
        <div class="dash-box">
          <h3 class="text-sm font-semibold mb-1">Typical requirements</h3>
          <ul class="text-[11px] text-slate-300 space-y-1">
            <li>• Good CGPA (7+ recommended)</li>
            <li>• IELTS / TOEFL / GRE as required</li>
            <li>• Strong SOP & LORs</li>
            <li>• 1–2 good projects / internships</li>
          </ul>
        </div>
        <div class="dash-box">
          <h3 class="text-sm font-semibold mb-1">How CareerTech helps (future)</h3>
          <ul class="text-[11px] text-slate-300 space-y-1">
            <li>• Profile evaluation</li>
            <li>• University shortlisting</li>
            <li>• SOP / CV feedback</li>
            <li>• Connecting with seniors and mentors</li>
          </ul>
        </div>
      </div>
    </div>
    """
    return render_page(content, "Study Abroad | CareerTech")


# -------------------- AI CAREER BOT --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-5">
  <h1 class="text-2xl md:text-3xl font-bold mb-1">CareerTech AI Mentor</h1>

  {% if not locked %}
    <p class="text-xs text-slate-300">
      Tell me your branch, year and interest. I’ll help you with roadmap, skills, projects and internships.
      You get one full chat session for free. Later this can be unlocked via subscription.
    </p>
  {% else %}
    <p class="text-xs text-slate-300">
      Your free AI career chat session is finished for this account.
      Please upgrade via the Subscription page to continue (demo message).
    </p>
  {% endif %}

  <form method="GET" action="/chatbot" class="mb-2">
    <input type="hidden" name="reset" value="1">
    <button class="px-3 py-1 rounded-full border border-slate-600 text-[10px] hover:bg-slate-800">
      🔄 Clear chat on screen
    </button>
  </form>

  <div class="bg-slate-900/80 border border-slate-700 rounded-2xl p-4 h-[340px] overflow-y-auto mb-3">
    {% if history %}
      {% for m in history %}
        <div class="mb-2">
          {% if m.role == 'user' %}
            <div class="text-[10px] text-slate-400 mb-0.5">You</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-indigo-600 text-[11px] max-w-[90%]">
              {{ m.content }}
            </div>
          {% else %}
            <div class="text-[10px] text-slate-400 mb-0.5">CareerTech AI</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-slate-800 text-[11px] max-w-[90%]">
              {{ m.content }}
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="text-[11px] text-slate-400">
        👋 Hi! I’m your CareerTech AI mentor. Start by telling me:
        your branch, year, rough CGPA and what you are interested in (e.g., web dev, AI, core, MS abroad).
      </p>
    {% endif %}
  </div>

  {% if not locked %}
    <form method="POST" class="flex gap-2">
      <input name="message" autocomplete="off" placeholder="Type your message here..." class="flex-1 input-box" required>
      <button class="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold">
        Send
      </button>
    </form>
    <form method="POST" action="/chatbot/end" class="mt-2">
      <button class="px-3 py-1.5 text-[10px] rounded-full border border-rose-500/70 text-rose-200 hover:bg-rose-500/10">
        🔒 End & lock free AI chat
      </button>
    </form>
  {% else %}
    <p class="text-[10px] text-slate-400 mt-1">
      Tip: Use your notes or screenshots from this chat to plan your next steps.
    </p>
  {% endif %}
</div>
"""


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    locked = bool(usage and usage.ai_used == 1)

    if request.args.get("reset") == "1":
        session["ai_history"] = []
        db.close()
        html = render_template_string(CHATBOT_HTML, history=[], locked=locked)
        return render_page(html, "CareerTech AI Mentor")

    history = session.get("ai_history", [])
    if not isinstance(history, list):
        history = []
    session["ai_history"] = history

    if request.method == "POST":
        if locked:
            history.append({
                "role": "assistant",
                "content": "⚠ Your free AI career chat has ended. Please upgrade via Subscription (demo)."
            })
            session["ai_history"] = history
            db.close()
            html = render_template_string(CHATBOT_HTML, history=history, locked=True)
            return render_page(html, "CareerTech AI Mentor")

        user_msg = request.form.get("message", "").strip()
        if user_msg:
            history.append({"role": "user", "content": user_msg})

            messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}] + history
            groq_client = get_groq_client()

            if groq_client is None:
                reply = "AI is not configured yet. Please ask admin to set GROQ_API_KEY on the server."
            else:
                try:
                    resp = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.7,
                    )
                    reply = resp.choices[0].message.content
                except Exception as e:
                    reply = f"AI error: {e}"

            history.append({"role": "assistant", "content": reply})
            session["ai_history"] = history

    db.close()
    html = render_template_string(CHATBOT_HTML, history=history, locked=locked)
    return render_page(html, "CareerTech AI Mentor")


@app.route("/chatbot/end", methods=["POST"])
def end_chatbot():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    try:
        usage = db.query(AiUsage).filter_by(user_id=user_id).first()
        if usage is None:
            usage = AiUsage(user_id=user_id, ai_used=1)
            db.add(usage)
        else:
            usage.ai_used = 1
        db.commit()
    finally:
        db.close()

    session["ai_history"] = []
    session["ai_used"] = True
    return redirect("/chatbot")


# -------------------- AI MOCK INTERVIEW --------------------
@app.route("/mock-interview", methods=["GET", "POST"])
def mock_interview():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    subscribed = user_is_subscribed(user_id)
    if not subscribed:
        content = """
        <div class="max-w-md mx-auto dash-box text-center space-y-3">
          <h2 class="text-xl font-bold mb-1">AI Mock Interview</h2>
          <p class="text-xs text-slate-300">
            This feature is available for subscribed users. It simulates HR + technical rounds with feedback.
          </p>
          <a href="/subscribe" class="px-4 py-2 rounded-full bg-indigo-600 text-xs font-semibold">
            Subscribe to unlock
          </a>
        </div>
        """
        return render_page(content, "Mock Interview (Locked)")

    history = session.get("mock_interview_history", [])
    if request.method == "POST":
        user_msg = request.form.get("message", "").strip()
        if user_msg:
            history.append({"role": "user", "content": user_msg})
            messages = [{
                "role": "system",
                "content": (
                    "You are an AI mock interviewer for engineering students. "
                    "Ask 1 question at a time from HR / basic technical topics. "
                    "Give short feedback on each answer. Stay supportive."
                )
            }] + history

            groq_client = get_groq_client()
            if groq_client is None:
                reply = "AI not configured. Please set GROQ_API_KEY."
            else:
                try:
                    resp = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.7,
                    )
                    reply = resp.choices[0].message.content
                except Exception as e:
                    reply = f"AI error: {e}"

            history.append({"role": "assistant", "content": reply})
            session["mock_interview_history"] = history

    bubbles = ""
    for m in history:
        who = "You" if m["role"] == "user" else "Interviewer"
        bg = "bg-indigo-600" if m["role"] == "user" else "bg-slate-800"
        bubbles += f"""
        <div class="mb-2">
          <div class="text-[10px] text-slate-400 mb-0.5">{who}</div>
          <div class="inline-block px-3 py-2 rounded-2xl {bg} text-[11px] max-w-[90%]">
            {m["content"]}
          </div>
        </div>
        """

    content = f"""
    <div class="max-w-3xl mx-auto space-y-4">
      <h2 class="text-2xl font-bold">AI Mock Interview</h2>
      <p class="text-xs text-slate-300">
        Type 'start' if you are beginning. Answer like you are in a real interview. You’ll get feedback as you go.
      </p>
      <div class="bg-slate-900/80 border border-slate-700 rounded-2xl p-4 h-[330px] overflow-y-auto mb-3">
        {bubbles if bubbles else "<p class='text-[11px] text-slate-400'>Session empty. Type 'start' to begin.</p>"}
      </div>
      <form method="POST" class="flex gap-2">
        <input name="message" autocomplete="off" placeholder="Type your answer or 'start'..." class="flex-1 input-box" required>
        <button class="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold">Send</button>
      </form>
    </div>
    """
    return render_page(content, "AI Mock Interview")


# -------------------- SUPPORT --------------------
@app.route("/support")
def support():
    content = """
    <div class="max-w-lg mx-auto space-y-4">
      <h2 class="text-2xl font-bold mb-1">Support & Help</h2>
      <p class="text-xs text-slate-300">
        For demo purposes, contact details below are placeholders. In a real system, this would connect to ticketing or WhatsApp.
      </p>
      <div class="dash-box">
        <p class="text-xs text-slate-300">📧 support@careertech.in</p>
        <p class="text-xs text-slate-300">📞 +91 98xx-xx-xxxx</p>
      </div>
    </div>
    """
    return render_page(content, "Support | CareerTech")


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
