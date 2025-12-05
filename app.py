import os
from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from groq import Groq

# -------------------- FLASK SETUP --------------------
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


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    level = Column(String(255), nullable=False)  # e.g. "B.Tech"
    track = Column(String(255), nullable=False)  # e.g. "CSE - AI & ML"


class College(Base):
    __tablename__ = "colleges"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    fees = Column(Integer, nullable=False)
    branch = Column(String(255), nullable=False)
    rating = Column(Float, nullable=False)


class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    speciality = Column(String(255), nullable=False)
    experience = Column(Text, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    salary = Column(String(255), nullable=False)
    track = Column(String(255), nullable=False)  # e.g. "AI/ML", "Full Stack"


# -------------------- AI (GROQ) --------------------
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


AI_SYSTEM_PROMPT = """
You are CareerTech's AI career guide for B.Tech students in India.

Your job:
- Talk like a friendly senior from a top tech company.
- Ask the student step by step:
  1) Branch & year (CSE, ECE, Mechanical, etc.).
  2) Skills so far (coding, DSA, dev, ML, etc.).
  3) Their dream role (SDE, Data Scientist, AI Engineer, DevOps, etc.).
  4) Whether they prefer higher studies, product companies, or startups.
  5) Time they can spend daily.

Then:
- Suggest a 3–6 month roadmap including:
  - Skills
  - Projects
  - Internships / profiles to build
- Mention realistic companies (Infosys, TCS, startups, product-based, etc.).
- Keep answers short, structured and motivating.

Very important:
- Do NOT claim guaranteed jobs.
- Make it clear this is guidance, not final placement advice.
"""


# -------------------- DB INIT & SEED --------------------
def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    if db.query(Course).count() == 0:
        courses_seed = [
            ("B.Tech CSE – Core Software Engineering", "B.Tech", "CSE"),
            ("B.Tech CSE – AI & Machine Learning", "B.Tech", "CSE - AI & ML"),
            ("B.Tech CSE – Data Science", "B.Tech", "CSE - Data Science"),
            ("B.Tech ECE – VLSI & Embedded Systems", "B.Tech", "ECE - VLSI"),
            ("B.Tech ECE – Communication Systems", "B.Tech", "ECE"),
            ("B.Tech IT – Full Stack Development", "B.Tech", "IT - Full Stack"),
            ("B.Tech Mechanical – Design & Manufacturing", "B.Tech", "Mechanical"),
            ("B.Tech Civil – Construction & Planning", "B.Tech", "Civil"),
            ("B.Tech EEE – Power & Automation", "B.Tech", "EEE"),
        ]
        for name, level, track in courses_seed:
            db.add(Course(name=name, level=level, track=track))

    if db.query(College).count() == 0:
        colleges_seed = [
            ("IIT Hyderabad", "Hyderabad, Telangana", 250000, "CSE", 4.9),
            ("IIIT Hyderabad", "Gachibowli, Hyderabad", 280000, "CSE - AI & ML", 4.8),
            ("JNTU Hyderabad (JNTUH)", "Kukatpally, Hyderabad", 80000, "CSE / ECE / EEE / Mech", 4.2),
            ("CBIT Hyderabad", "Gandipet, Hyderabad", 150000, "CSE / IT / ECE / EEE", 4.3),
            ("VNR VJIET", "Bachupally, Hyderabad", 160000, "CSE / ECE / Mech", 4.4),
            ("Gokaraju Rangaraju (GRIET)", "Nizampet, Hyderabad", 135000, "CSE / AI / DS / ECE", 4.1),
            ("Vasavi College of Engineering", "Ibrahimbagh, Hyderabad", 170000, "CSE / IT / ECE / Civil", 4.5),
            ("MLRIT", "Dundigal, Hyderabad", 120000, "CSE / AI & ML / DS", 4.0),
        ]
        for name, loc, fees, branch, rating in colleges_seed:
            db.add(College(name=name, location=loc, fees=fees, branch=branch, rating=rating))

    if db.query(Mentor).count() == 0:
        mentors_seed = [
            ("Krishna P.", "Senior Software Engineer", "Microsoft", "System Design & DSA",
             "8+ years in backend, system design interviews, and product-based hiring."),
            ("Ananya R.", "Data Scientist", "Top FinTech Startup", "Data Science & ML",
             "Worked on fraud detection, ML pipelines, and MLOps."),
            ("Rahul S.", "SDE 2", "Amazon", "Low-level design & coding",
             "Helped 100+ students crack SDE roles in product companies."),
        ]
        for n, role, company, spec, exp in mentors_seed:
            db.add(Mentor(name=n, role=role, company=company, speciality=spec, experience=exp))

    if db.query(Job).count() == 0:
        jobs_seed = [
            ("Software Development Engineer (SDE 1)", "Amazon / Microsoft / Flipkart", "Bangalore / Hyderabad",
             "₹18–25 LPA (varies)", "SDE / Backend"),
            ("Data Analyst / Junior Data Scientist", "FinTech / Product Startups", "Hyderabad / Pune / Remote",
             "₹6–12 LPA", "Data / Analytics"),
            ("Full Stack Developer", "SaaS & Startup Companies", "Remote / Bangalore", "₹5–15 LPA", "Full Stack"),
            ("AI/ML Engineer", "AI First Startups", "Bangalore / Remote", "₹10–22 LPA", "AI/ML"),
        ]
        for title, company, loc, sal, track in jobs_seed:
            db.add(Job(title=title, company=company, location=loc, salary=sal, track=track))

    db.commit()
    db.close()


init_db()

# -------------------- BASE LAYOUT (ULTRA-MODERN) --------------------
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title or "CareerTech" }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="bg-[#020617] text-slate-50">

<div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">

  <!-- NAVBAR -->
  <nav class="flex justify-between items-center px-5 md:px-10 py-4 bg-black/40 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-40">
    <!-- LOGO + TITLE -->
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 md:w-12 md:h-12 rounded-2xl bg-gradient-to-br from-cyan-500 via-indigo-500 to-purple-500 flex items-center justify-center shadow-[0_0_40px_rgba(56,189,248,0.6)]">
        <span class="text-xl md:text-2xl font-black tracking-tight">CT</span>
      </div>
      <div>
        <p class="font-semibold text-lg md:text-xl tracking-tight">CareerTech</p>
        <p class="text-[11px] text-slate-400">B.Tech · Skills · Projects · Jobs</p>
      </div>
    </div>

    <!-- NAV LINKS -->
    <div class="hidden lg:flex items-center gap-6 text-sm">
      <a href="{{ url_for('home') }}" class="nav-link">Home</a>
      <a href="{{ url_for('courses') }}" class="nav-link">Courses</a>
      <a href="{{ url_for('colleges') }}" class="nav-link">Colleges</a>
      <a href="{{ url_for('mentorship') }}" class="nav-link">Mentors</a>
      <a href="{{ url_for('jobs') }}" class="nav-link">Jobs</a>
      <a href="{{ url_for('global_match') }}" class="nav-link">Global Match</a>
      <a href="{{ url_for('chatbot') }}" class="nav-link">AI Career Bot</a>

      {% if session.get('user_name') %}
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/70 border border-slate-700">
            <div class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-xs font-semibold">
              {{ session.get('user_name')[0]|upper }}
            </div>
            <div class="leading-tight">
              <p class="text-[11px] text-slate-400">Logged in as</p>
              <p class="text-xs font-semibold truncate max-w-[110px]">{{ session.get('user_name') }}</p>
            </div>
          </div>
          <a href="{{ url_for('dashboard') }}" class="px-3 py-1.5 rounded-full text-[12px] border border-indigo-500/80 bg-indigo-500/10 hover:bg-indigo-500/20">
            Dashboard
          </a>
          <a href="{{ url_for('logout') }}" class="px-3 py-1.5 rounded-full text-[12px] bg-rose-500 hover:bg-rose-600 shadow shadow-rose-500/40">
            Logout
          </a>
        </div>
      {% else %}
        <div class="flex items-center gap-3">
          <a href="{{ url_for('login') }}" class="px-4 py-1.5 rounded-full bg-slate-900/80 border border-slate-700 text-xs font-medium hover:bg-slate-800">
            Login
          </a>
          <a href="{{ url_for('signup') }}" class="px-4 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-xs font-semibold shadow shadow-indigo-500/50">
            Get Started
          </a>
        </div>
      {% endif %}
    </div>

    <!-- MOBILE -->
    <div class="lg:hidden flex items-center gap-3">
      {% if session.get('user_name') %}
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-xs font-semibold">
          {{ session.get('user_name')[0]|upper }}
        </div>
      {% endif %}
    </div>
  </nav>

  <!-- PAGE CONTENT -->
  <main class="px-4 md:px-10 py-8">
    {{ content|safe }}
  </main>

</div>

<!-- AI POPUP -->
<button id="aiFab" class="ai-fab">
  <div class="ai-fab-inner">
    <span class="text-2xl">🤖</span>
  </div>
  <span class="ai-fab-pulse"></span>
</button>

<div id="aiModalBg" class="ai-modal-bg"></div>

<div id="aiModal" class="ai-modal">
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-sm">
        🤖
      </div>
      <div>
        <p class="text-sm font-semibold">CareerTech AI</p>
        <p class="text-[11px] text-slate-400">Your personal tech career co-pilot</p>
      </div>
    </div>
    <button id="closeAi" class="text-slate-400 hover:text-slate-100 text-lg leading-none">&times;</button>
  </div>
  <p class="text-xs text-slate-300 mb-3">
    Ask anything about B.Tech careers, skills, projects or interviews.
  </p>
  <div class="flex flex-col gap-2">
    <a href="{{ url_for('chatbot') }}" class="ai-modal-btn-primary">
      Start AI Career Chat
    </a>
    <a href="{{ url_for('jobs') }}" class="ai-modal-btn-ghost">
      View trending tech roles
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

  aiFab.addEventListener('click', openAi);
  aiModalBg.addEventListener('click', closeAiModal);
  closeAi.addEventListener('click', closeAiModal);

  // Auto-attention after few seconds on first visit
  setTimeout(() => {
    if (!sessionStorage.getItem('ai_seen')) {
      openAi();
      sessionStorage.setItem('ai_seen', '1');
    }
  }, 4000);
</script>

</body>
</html>
"""


def render_page(content_html, title="CareerTech"):
    return render_template_string(BASE_HTML, content=content_html, title=title)


# -------------------- HOME --------------------
@app.route("/")
def home():
    user_name = session.get("user_name")

    if user_name:
        greeting = "Welcome back, " + user_name.split()[0]
    else:
        greeting = "Build your tech career, step by step."

    content = f"""
    <div class="max-w-6xl mx-auto space-y-12 hero-shell">
      <!-- HERO -->
      <section class="grid md:grid-cols-2 gap-10 items-center">
        <div class="space-y-4">
          <span class="pill-badge">
            <span class="pill-dot"></span>
            B.Tech · Career Intelligence Platform
          </span>

          <h1 class="hero-title">
            Turn your <span class="gradient-text">B-Tech degree</span> into a real tech career.
          </h1>

          <p class="hero-sub">
            CareerTech gives B.Tech students branch-based roadmaps, skills, projects, mentors and AI guidance — all in one place.
          </p>

          <div class="flex flex-wrap items-center gap-3 mt-2">
            <a href="{url_for('signup')}" class="primary-cta">
              🚀 Get started – ₹299 / year (demo)
            </a>
            <a href="{url_for('chatbot')}" class="ghost-cta">
              🤖 Try AI career planner
            </a>
          </div>

          <p class="hero-footnote">
            Designed for CSE, ECE, IT, Mechanical, Civil, EEE and more. Built for Indian engineering colleges.
          </p>
        </div>

        <!-- RIGHT: BIG DASHBOARD PREVIEW CARD -->
        <div class="hero-card">
          <p class="text-[11px] text-cyan-300 uppercase tracking-[0.25em] mb-2">Student Snapshot</p>
          <h3 class="text-lg font-semibold mb-3">B.Tech CSE · 3rd Year · Career Overview</h3>
          <div class="grid grid-cols-2 gap-4 mb-5">
            <div class="dash-chip">
              <p class="chip-label">Career Track</p>
              <p class="chip-value">SDE · Backend</p>
            </div>
            <div class="dash-chip">
              <p class="chip-label">Readiness</p>
              <p class="chip-value">3.5 / 5</p>
            </div>
            <div class="dash-chip">
              <p class="chip-label">Core Stack</p>
              <p class="chip-value">DSA · Java · SQL</p>
            </div>
            <div class="dash-chip">
              <p class="chip-label">Next 30 days</p>
              <p class="chip-value">2 projects · 40 DSA</p>
            </div>
          </div>
          <p class="text-[11px] text-slate-400 mb-1">Powered by branch-based roadmaps, mentor inputs and AI planning.</p>
          <div class="flex items-center gap-2">
            <div class="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
              <div class="h-full w-3/4 bg-gradient-to-r from-cyan-400 via-indigo-500 to-purple-500"></div>
            </div>
            <span class="text-[11px] text-slate-300">75% Journey mapped</span>
          </div>
        </div>
      </section>

      <!-- FEATURE GRID -->
      <section class="space-y-4">
        <h3 class="section-title">CareerTech Spaces</h3>
        <p class="section-sub">
          All the key pieces B.Tech students need – brought into one clean interface.
        </p>

        <div class="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <a href="{url_for('courses')}" class="feature-card">
            <span class="feature-icon">📚</span>
            <div>
              <p class="feature-title">Branch Courses</p>
              <p class="feature-sub">CSE, ECE, IT, Mech, Civil, EEE & more.</p>
            </div>
          </a>

          <a href="{url_for('colleges')}" class="feature-card">
            <span class="feature-icon">🏫</span>
            <div>
              <p class="feature-title">Colleges Map</p>
              <p class="feature-sub">Fees, branches & ratings snapshot.</p>
            </div>
          </a>

          <a href="{url_for('mentorship')}" class="feature-card">
            <span class="feature-icon">🧑‍💻</span>
            <div>
              <p class="feature-title">Mentors</p>
              <p class="feature-sub">SDEs, Data Scientists, startup engineers.</p>
            </div>
          </a>

          <a href="{url_for('jobs')}" class="feature-card">
            <span class="feature-icon">💼</span>
            <div>
              <p class="feature-title">Jobs & Roles</p>
              <p class="feature-sub">SDE, Data, AI, Full Stack & more.</p>
            </div>
          </a>

          <a href="{url_for('global_match')}" class="feature-card">
            <span class="feature-icon">🌍</span>
            <div>
              <p class="feature-title">Global Match</p>
              <p class="feature-sub">MS / Masters & global tech paths.</p>
            </div>
          </a>

          <a href="{url_for('chatbot')}" class="feature-card">
            <span class="feature-icon">🤖</span>
            <div>
              <p class="feature-title">AI Career Bot</p>
              <p class="feature-sub">Personalised tech roadmap in minutes.</p>
            </div>
          </a>
        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerTech | Home")


# -------------------- AUTH --------------------
SIGNUP_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl md:text-2xl font-bold mb-2">Create your CareerTech account</h2>
  <p class="text-xs text-slate-400 mb-4">For B.Tech, diploma and fresh engineering graduates.</p>
  <input name="name" placeholder="Full Name" required class="input-box">
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Sign up</button>
  <p class="text-slate-400 mt-3 text-xs">
    Already registered?
    <a href="/login" class="text-cyan-300 hover:underline">Login</a>
  </p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl md:text-2xl font-bold mb-2">Login to CareerTech</h2>
  <p class="text-xs text-slate-400 mb-4">Continue your tech career journey.</p>
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Login</button>
  <p class="text-slate-400 mt-3 text-xs">
    New here?
    <a href="/signup" class="text-cyan-300 hover:underline">Create Account</a>
  </p>
</form>
"""


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return render_page(
                "<p class='error-text'>All fields are required.</p>" + SIGNUP_FORM,
                "Signup"
            )

        db = get_db()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.close()
            return render_page(
                "<p class='error-text'>Account already exists. Please login.</p>" + SIGNUP_FORM,
                "Signup"
            )

        hashed = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        user = User(name=name, email=email, password=hashed)
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

        ok = False
        if user:
            try:
                ok = check_password_hash(user.password, password)
            except Exception:
                ok = (user.password == password)

        if ok:
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["ai_history"] = []
            return redirect("/dashboard")

        return render_page(
            "<p class='error-text'>Invalid email or password.</p>" + LOGIN_FORM,
            "Login"
        )

    return render_page(LOGIN_FORM, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    name = session.get("user_name", "Student").split()[0]

    content = f"""
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="flex flex-wrap justify-between gap-3 items-end">
        <div>
          <p class="text-xs text-slate-400 mb-1">Student Dashboard · CareerTech</p>
          <h1 class="text-2xl md:text-3xl font-bold">Hi {name}, here's your tech journey snapshot ⚡</h1>
        </div>
        <a href="{url_for('chatbot')}" class="px-3 py-1.5 rounded-full text-xs bg-gradient-to-r from-cyan-500 to-indigo-500 shadow shadow-cyan-500/40">
          Ask AI: “What should I do next?”
        </a>
      </div>

      <div class="grid md:grid-cols-3 gap-4">
        <div class="dash-card">
          <p class="dash-label">Status</p>
          <p class="dash-value">Planning tech career</p>
          <p class="dash-foot">Roadmap: Skills · Projects · Internships.</p>
        </div>
        <div class="dash-card">
          <p class="dash-label">Focus Tracks</p>
          <p class="dash-value">SDE / Data / AI</p>
          <p class="dash-foot">Choose 1–2 max and go deep.</p>
        </div>
        <div class="dash-card">
          <p class="dash-label">Next 30 days</p>
          <p class="dash-value">Build 1 strong project</p>
          <p class="dash-foot">Show skills instead of marks.</p>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
          <h3 class="section-title mb-2">CareerTech guidance</h3>
          <ul class="text-xs md:text-sm text-slate-300 space-y-1.5">
            <li>• Pick a primary track: <b>SDE</b>, <b>Data</b>, <b>AI/ML</b>, <b>DevOps</b> or <b>Core</b>.</li>
            <li>• Do 2–3 <b>resume-worthy projects</b> instead of 10 tiny ones.</li>
            <li>• Practice <b>DSA or problem-solving</b> at least 30–45 mins daily.</li>
            <li>• Maintain a clean <b>GitHub</b> and <b>LinkedIn</b> profile.</li>
            <li>• Use the AI bot for roadmap suggestions and project ideas.</li>
          </ul>
        </div>

        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
          <h3 class="section-title mb-2">How to use this website (quick walkthrough)</h3>
          <ol class="text-xs md:text-sm text-slate-300 space-y-1.5 list-decimal list-inside">
            <li>Open <b>Courses</b> to see branch-wise options and specializations.</li>
            <li>Check <b>Colleges</b> with filters by budget & rating.</li>
            <li>Explore <b>Jobs</b> to understand real roles & packages.</li>
            <li>Talk to <b>Mentors</b> (demo) to simulate real guidance.</li>
            <li>Use <b>AI Career Bot</b> to generate a personalised plan.</li>
          </ol>
          <p class="text-[11px] text-slate-400 mt-3">
            Video idea (for demo): One screen recording (2–3 mins) where a student logs in, checks colleges, views jobs and chats with AI.
          </p>
        </div>
      </div>
    </div>
    """
    return render_page(content, "Dashboard | CareerTech")


# -------------------- COURSES --------------------
@app.route("/courses")
def courses():
    db = get_db()
    data = db.query(Course).order_by(Course.level.asc(), Course.name.asc()).all()
    db.close()

    rows = ""
    for c in data:
        rows += f"""
        <tr>
          <td>{c.level}</td>
          <td>{c.name}</td>
          <td>{c.track}</td>
        </tr>
        """

    if not rows:
        rows = "<tr><td colspan='3'>No courses found yet.</td></tr>"

    content = f"""
    <div class="max-w-5xl mx-auto">
      <h2 class="page-title">Branch-based Courses & Tracks</h2>
      <p class="page-sub">
        These are example B.Tech specializations and tracks students commonly pursue in India.
        Exact names depend on each college and university.
      </p>

      <table class="table mt-4">
        <tr>
          <th>Level</th>
          <th>Course / Specialization</th>
          <th>Track / Branch</th>
        </tr>
        {rows}
      </table>
    </div>
    """
    return render_page(content, "Courses | CareerTech")


# -------------------- COLLEGES --------------------
@app.route("/colleges")
def colleges():
    budget = request.args.get("budget", "").strip()
    branch = request.args.get("branch", "").strip()
    rating_min = request.args.get("rating", "").strip()

    db = get_db()
    query = db.query(College)

    if budget == "lt1":
        query = query.filter(College.fees < 100000)
    elif budget == "b1_2":
        query = query.filter(College.fees.between(100000, 200000))
    elif budget == "gt2":
        query = query.filter(College.fees > 200000)

    if branch:
        query = query.filter(College.branch.ilike(f"%{branch}%"))

    if rating_min:
        try:
            val = float(rating_min)
            query = query.filter(College.rating >= val)
        except ValueError:
            pass

    data = query.order_by(College.rating.desc()).all()
    db.close()

    rows = ""
    for col in data:
        rows += f"""
        <tr>
          <td>{col.name}</td>
          <td>{col.branch}</td>
          <td>{col.location}</td>
          <td>₹{col.fees:,}</td>
          <td>{col.rating:.1f}★</td>
        </tr>
        """

    if not rows:
        rows = "<tr><td colspan='5'>No colleges match this filter yet.</td></tr>"

    sel_b_any = "selected" if budget == "" else ""
    sel_b_lt1 = "selected" if budget == "lt1" else ""
    sel_b_b1_2 = "selected" if budget == "b1_2" else ""
    sel_b_gt2 = "selected" if budget == "gt2" else ""

    sel_r_any = "selected" if rating_min == "" else ""
    sel_r_4 = "selected" if rating_min == "4.0" else ""
    sel_r_45 = "selected" if rating_min == "4.5" else ""

    content = f"""
    <div class="max-w-6xl mx-auto">
      <h2 class="page-title">B.Tech Colleges – Snapshot (Hyderabad Focus)</h2>
      <p class="page-sub">
        Fees and ratings below are indicative for demo purposes. Always confirm with official college sources.
      </p>

      <form method="GET" class="grid md:grid-cols-4 gap-3 mt-4 mb-3 items-end">
        <div>
          <label class="filter-label">Budget (Tuition / Year)</label>
          <select name="budget" class="search-bar">
            <option value="" {sel_b_any}>Any budget</option>
            <option value="lt1" {sel_b_lt1}>Below ₹1,00,000</option>
            <option value="b1_2" {sel_b_b1_2}>₹1,00,000 – ₹2,00,000</option>
            <option value="gt2" {sel_b_gt2}>Above ₹2,00,000</option>
          </select>
        </div>

        <div>
          <label class="filter-label">Branch / Track</label>
          <input name="branch" value="{branch}" placeholder="e.g. CSE, AI, ECE" class="search-bar" />
        </div>

        <div>
          <label class="filter-label">Min Rating</label>
          <select name="rating" class="search-bar">
            <option value="" {sel_r_any}>Any rating</option>
            <option value="4.0" {sel_r_4}>4.0★ & above</option>
            <option value="4.5" {sel_r_45}>4.5★ & above</option>
          </select>
        </div>

        <div>
          <button class="w-full px-3 py-2 bg-indigo-600 rounded-xl text-sm font-medium hover:bg-indigo-500">
            Apply filters
          </button>
        </div>
      </form>

      <table class="table mt-2">
        <tr>
          <th>College</th>
          <th>Branches / Tracks</th>
          <th>Location</th>
          <th>Approx Fees / Year</th>
          <th>Rating</th>
        </tr>
        {rows}
      </table>
    </div>
    """
    return render_page(content, "Colleges | CareerTech")


# -------------------- MENTORS --------------------
@app.route("/mentorship")
def mentorship():
    db = get_db()
    data = db.query(Mentor).all()
    db.close()

    cards = ""
    for m in data:
        cards += f"""
        <div class="mentor-card">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-base font-semibold">{m.name}</h3>
              <p class="text-[11px] text-cyan-300">{m.role} · {m.company}</p>
            </div>
            <span class="mentor-tag">{m.speciality}</span>
          </div>
          <p class="text-xs text-slate-300 mb-3">{m.experience}</p>
          <button class="mentor-btn">Book mock call (demo)</button>
        </div>
        """

    content = f"""
    <div class="max-w-6xl mx-auto space-y-4">
      <h2 class="page-title">Mentors · Real Engineers, Real Guidance</h2>
      <p class="page-sub">
        These are sample mentor profiles to show how CareerTech can connect students with real SDEs, Data Scientists and AI Engineers.
      </p>

      <div class="grid md:grid-cols-3 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Mentors | CareerTech")


# -------------------- JOBS --------------------
@app.route("/jobs")
def jobs():
    db = get_db()
    data = db.query(Job).all()
    db.close()

    cards = ""
    for j in data:
        cards += f"""
        <div class="job-card">
          <p class="job-title">{j.title}</p>
          <p class="job-company">{j.company}</p>
          <p class="job-meta">{j.location}</p>
          <p class="job-salary">{j.salary}</p>
          <p class="job-track">Track: {j.track}</p>
        </div>
        """

    content = f"""
    <div class="max-w-6xl mx-auto space-y-4">
      <h2 class="page-title">Jobs & Role Landscape</h2>
      <p class="page-sub">
        These are example tech roles B.Tech grads aim for. Packages and locations are indicative (demo).
      </p>
      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Jobs | CareerTech")


# -------------------- GLOBAL MATCH --------------------
@app.route("/global-match")
def global_match():
    content = """
    <div class="max-w-5xl mx-auto space-y-4">
      <h2 class="page-title">Global Match – MS & Tech Pathways</h2>
      <p class="page-sub">
        Many B.Tech students plan for MS in CS / AI / Data abroad. This section gives a high-level view (demo).
      </p>

      <div class="grid md:grid-cols-3 gap-4">
        <div class="support-box">
          <h3 class="section-title mb-2">Popular Countries</h3>
          <ul class="support-list">
            <li>• USA – MS in CS, AI, Data</li>
            <li>• Canada – PG diplomas in IT, Data</li>
            <li>• Germany – TU universities (low fees)</li>
            <li>• UK – 1-year masters in CS / AI</li>
          </ul>
        </div>

        <div class="support-box">
          <h3 class="section-title mb-2">Typical Requirements</h3>
          <ul class="support-list">
            <li>• Solid CGPA & strong projects</li>
            <li>• GRE/IELTS/TOEFL (varies)</li>
            <li>• SOP + LORs showcasing impact</li>
            <li>• Clear goal: role / research area</li>
          </ul>
        </div>

        <div class="support-box">
          <h3 class="section-title mb-2">CareerTech's Role (vision)</h3>
          <ul class="support-list">
            <li>• Build MS-focused 2-year roadmap</li>
            <li>• Suggest projects + research areas</li>
            <li>• Profile-building checklist</li>
            <li>• Connect with mentors abroad</li>
          </ul>
        </div>
      </div>
    </div>
    """
    return render_page(content, "Global Match | CareerTech")


# -------------------- AI CAREER BOT --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-6">
  <h1 class="text-2xl md:text-3xl font-bold">CareerTech AI Mentor</h1>
  <p class="text-sm text-slate-300">
    Chat with an AI that behaves like a senior from a top tech company. It will ask about your branch, skills and goals – and then suggest a realistic plan.
  </p>

  <form method="GET" action="/chatbot" class="mb-2">
    <input type="hidden" name="reset" value="1">
    <button class="text-[11px] px-3 py-1 rounded-full border border-slate-600 hover:bg-slate-800">
      🔄 Clear chat on screen
    </button>
  </form>

  <div class="bg-slate-950/70 border border-slate-800 rounded-2xl p-4 h-[360px] overflow-y-auto mb-3">
    {% if history %}
      {% for m in history %}
        <div class="mb-3">
          {% if m.role == 'user' %}
            <div class="text-[10px] text-slate-400 mb-0.5">You</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-indigo-600 text-xs md:text-sm max-w-[90%]">
              {{ m.content }}
            </div>
          {% else %}
            <div class="text-[10px] text-slate-400 mb-0.5">CareerTech AI</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-slate-800 text-xs md:text-sm max-w-[90%]">
              {{ m.content }}
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="text-sm text-slate-400">
        👋 Start by saying: “I am a 3rd year CSE student, I know basic Python and C, I want SDE role.”
      </p>
    {% endif %}
  </div>

  <form method="POST" class="flex gap-2">
    <input
      name="message"
      autocomplete="off"
      placeholder="Type your message here..."
      class="flex-1 input-box"
      required
    >
    <button class="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold">
      Send
    </button>
  </form>
</div>
"""


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    user_id = session.get("user_id")
    if not user_id:
        # allow viewing page but redirect to login for real use if you want
        pass

    if request.args.get("reset") == "1":
        session["ai_history"] = []
        return redirect("/chatbot")

    history = session.get("ai_history", [])
    if not isinstance(history, list):
        history = []
    session["ai_history"] = history

    if request.method == "POST":
        user_msg = request.form.get("message", "").strip()
        if user_msg:
            history.append({"role": "user", "content": user_msg})
            groq_client = get_groq_client()

            if groq_client is None:
                reply = (
                    "AI backend (Groq) is not configured yet.\n"
                    "Once configured with a GROQ_API_KEY, this will give you a live roadmap."
                )
            else:
                try:
                    messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}] + history
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

    html = render_template_string(CHATBOT_HTML, history=history)
    return render_page(html, "AI Mentor | CareerTech")


# -------------------- SUPPORT --------------------
@app.route("/support")
def support():
    content = """
    <div class="max-w-xl mx-auto space-y-3">
      <h2 class="page-title">Support & Contact</h2>
      <p class="page-sub">Prototype only – replace with real contact details later.</p>
      <div class="support-box">
        <p>📧 support@careertech.in (demo)</p>
        <p>📍 Hyderabad, India</p>
      </div>
    </div>
    """
    return render_page(content, "Support | CareerTech")


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
