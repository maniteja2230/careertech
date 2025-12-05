import os
from flask import (
    Flask, request, redirect, session,
    render_template_string
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from groq import Groq

# -------------------- FLASK SETUP --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careertech_secret_key")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careertech.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()


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
    category = Column(String(255), nullable=False)  # CSE, ECE, etc.


class College(Base):
    __tablename__ = "colleges"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=False)  # CSE / ECE / etc (main strength)
    fees = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)


class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    experience = Column(Text, nullable=False)
    speciality = Column(String(255), nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    stipend = Column(String(255), nullable=False)


class AiUsage(Base):
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    used = Column(Integer, nullable=False, default=0)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    branch = Column(String(255), nullable=True)
    year = Column(String(50), nullable=True)
    skills = Column(Text, nullable=True)
    dream_roles = Column(Text, nullable=True)
    resume_link = Column(String(500), nullable=True)


def get_db():
    return SessionLocal()


def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    # ---- Seed courses ----
    if db.query(Course).count() == 0:
        courses_seed = [
            ("Full Stack Web Development (MERN)", "CSE / IT"),
            ("Data Science & Machine Learning with Python", "CSE / IT / AI"),
            ("DSA & Competitive Programming Track", "CSE / IT"),
            ("Embedded Systems & IoT", "ECE / EEE"),
            ("VLSI & Chip Design Basics", "ECE"),
            ("Robotics & Industrial Automation", "Mechanical / Mechatronics"),
            ("Cloud & DevOps (AWS + Docker + CI/CD)", "CSE / IT"),
            ("Cyber Security & Ethical Hacking", "CSE / IT"),
            ("AI & GenAI for Engineers", "CSE / AI / DS"),
            ("CATIA / Solidworks for Design Engineers", "Mechanical"),
        ]
        for name, cat in courses_seed:
            db.add(Course(name=name, category=cat))

    # ---- Seed colleges (example data) ----
    if db.query(College).count() == 0:
        colleges_seed = [
            ("IIT Hyderabad", "Hyderabad, Telangana", "CSE / AI", 250000, 4.8),
            ("IIIT Hyderabad", "Gachibowli, Hyderabad", "CSE", 280000, 4.7),
            ("JNTU Hyderabad", "Kukatpally, Hyderabad", "CSE / ECE / ME", 90000, 4.3),
            ("VNR VJIET", "Bachupally, Hyderabad", "CSE / ECE", 160000, 4.4),
            ("CVR College of Engineering", "Ibrahimpatnam, Hyderabad", "CSE / IT / ECE", 130000, 4.2),
            ("Gokaraju Rangaraju (GRIET)", "Nizampet, Hyderabad", "CSE / ECE / EEE", 150000, 4.3),
            ("MLRIT", "Dundigal, Hyderabad", "CSE / AIML / DS", 140000, 4.1),
            ("CMR College of Engineering & Tech", "Medchal Road, Hyderabad", "CSE / IT", 135000, 4.0),
            ("Vasavi College of Engineering", "Ibrahimbagh, Hyderabad", "CSE / ECE / CIVIL", 175000, 4.5),
            ("SR University", "Warangal Highway, Telangana", "CSE / AI / Robotics", 180000, 4.4),
        ]
        for name, loc, branch, fees, rating in colleges_seed:
            db.add(College(name=name, location=loc, branch=branch, fees=fees, rating=rating))

    # ---- Seed mentors ----
    if db.query(Mentor).count() == 0:
        mentors_seed = [
            ("Krishna P.", "Senior Data Engineer @ Product Company",
             "8+ years in data platforms, pipelines & analytics.",
             "Data Engineering / Data Science Roadmaps"),
            ("Ananya R.", "SDE-II @ FAANG-like company",
             "Backend + system design + DSA interview prep.",
             "Full Stack / Backend / DSA"),
            ("Mohammed A.", "Cloud & DevOps Consultant",
             "Helped 100+ students move into DevOps roles.",
             "DevOps / Cloud / SRE"),
            ("Tejaswini S.", "Robotics Engineer",
             "Works on industrial automation & robotics startups.",
             "Robotics / Embedded / IoT"),
        ]
        for n, role, exp, spec in mentors_seed:
            db.add(Mentor(name=n, role=role, experience=exp, speciality=spec))

    # ---- Seed jobs (internships snapshot) ----
    if db.query(Job).count() == 0:
        jobs_seed = [
            ("Backend Developer Intern (Python / FastAPI)", "Early-stage SaaS Startup", "Remote", "₹15k–25k / month"),
            ("Data Science Intern (ML + Dashboards)", "Analytics Firm", "Hyderabad / Remote", "₹10k–20k / month"),
            ("DevOps Intern (AWS + CI/CD)", "Cloud Consulting Company", "Hyderabad", "₹12k–18k / month"),
            ("Front-end React Intern", "EdTech Startup", "Hybrid – Hyderabad", "₹8k–15k / month"),
            ("Embedded & IoT Intern", "Industrial Automation Company", "On-site – Hyderabad", "₹10k–15k / month"),
        ]
        for title, company, loc, stipend in jobs_seed:
            db.add(Job(title=title, company=company, location=loc, stipend=stipend))

    db.commit()
    db.close()


@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


init_db()


# -------------------- GROQ HELPER --------------------
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


AI_SYSTEM_PROMPT = """
You are CareerTech's AI mentor for B-Tech students in India.

Act like a friendly senior from a good product-based company.
Ask step-by-step:
1) Name, college, year and branch.
2) Current skills (coding, tools, projects) and comfort with DSA.
3) Target roles (SDE, Data Science, DevOps, Cybersecurity, Core).
4) Time available per day and graduation year.
5) Whether they want India jobs, remote work, or abroad.

Then:
- Suggest a realistic 6–12 month roadmap.
- Include 2–3 project ideas.
- Suggest online resources and topics (DSA, CS fundamentals, tools).
- Keep answers short, clear and motivating.
"""


# -------------------- BASE HTML LAYOUT --------------------
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  {% if title %}
    <title>{{ title }}</title>
  {% else %}
    <title>CareerTech</title>
  {% endif %}
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-slate-950 text-white font-[system-ui]">

<div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">

  <!-- NAVBAR -->
  <nav class="flex items-center justify-between px-5 md:px-10 py-4 bg-black/40 backdrop-blur-md border-b border-slate-800">
    <!-- Left: logo & title -->
    <div class="flex items-center gap-3">
      <div class="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center shadow-lg shadow-indigo-500/40">
        <!-- You can replace this with your logo image -->
        <span class="text-xl font-bold text-indigo-400">CT</span>
      </div>
      <div>
        <p class="font-bold text-lg md:text-xl tracking-tight">CareerTech</p>
        <p class="text-[11px] text-slate-400">B-Tech Careers · Roadmaps · Internships</p>
      </div>
    </div>

    <!-- Right: links + user -->
    <div class="hidden md:flex items-center gap-5 text-sm">
      <a href="/" class="nav-link">Home</a>
      <a href="/courses" class="nav-link">Courses</a>
      <a href="/colleges" class="nav-link">Colleges</a>
      <a href="/mentors" class="nav-link">Mentors</a>
      <a href="/jobs" class="nav-link">Jobs</a>
      <a href="/global-match" class="nav-link">Global Path</a>
      <a href="/chatbot" class="nav-link">AI Mentor</a>

      {% if session.get('user') %}
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-700">
          <div class="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-semibold">
            {{ session.get('user')[0]|upper }}
          </div>
          <div class="flex flex-col leading-tight">
            <span class="text-[11px] text-slate-400 block">Logged in as</span>
            <a href="/dashboard" class="text-[13px] font-semibold hover:text-indigo-300 truncate max-w-[120px]">
              {{ session.get('user') }}
            </a>
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

  <!-- CONTENT -->
  <main class="px-4 md:px-10 py-8">
    {{ content|safe }}
  </main>
</div>

<!-- AI floating button -->
<button id="aiFab"
  class="fixed right-4 bottom-4 z-40 flex items-center gap-2 px-4 py-3 rounded-full shadow-xl bg-indigo-600 hover:bg-indigo-500 hover:scale-105 transition transform">
  <span class="text-2xl">🤖</span>
  <span class="text-xs text-left leading-tight">
    <span class="font-semibold block">Need help?</span>
    <span class="text-[10px] text-indigo-100">Ask CareerTech AI</span>
  </span>
</button>

<!-- popup -->
<div id="aiOverlay" class="hidden fixed inset-0 bg-black/60 z-40"></div>
<div id="aiPopup" class="hidden fixed right-4 bottom-20 w-[360px] max-w-[94vw] bg-slate-900/95 border border-indigo-500/60 rounded-2xl shadow-2xl p-4 z-50">
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <span class="text-2xl">🤖</span>
      <div>
        <p class="text-sm font-semibold">CareerTech AI Mentor</p>
        <p class="text-[10px] text-slate-400">Gets you a roadmap in under a minute.</p>
      </div>
    </div>
    <button id="aiClose" class="text-slate-400 hover:text-white text-lg">✕</button>
  </div>
  <p class="text-xs text-slate-300 mb-3">
    Ask doubts on skills, projects, internships or placements. Start by telling your branch &amp; year.
  </p>
  <div class="flex flex-col gap-2">
    <a href="/chatbot" class="w-full primary-cta text-center text-xs py-2.5">Open AI Career Mentor</a>
    <a href="/dashboard" class="w-full text-[11px] text-center px-3 py-2 rounded-full border border-slate-600 hover:bg-slate-800">
      View your profile &amp; roadmap
    </a>
  </div>
</div>

<script>
  const fab = document.getElementById('aiFab');
  const popup = document.getElementById('aiPopup');
  const overlay = document.getElementById('aiOverlay');
  const closeBtn = document.getElementById('aiClose');

  function openPopup() {
    popup.classList.remove('hidden');
    overlay.classList.remove('hidden');
  }
  function closePopup() {
    popup.classList.add('hidden');
    overlay.classList.add('hidden');
  }

  fab.addEventListener('click', openPopup);
  overlay.addEventListener('click', closePopup);
  closeBtn.addEventListener('click', closePopup);
</script>

</body>
</html>
"""


def render_page(content_html, title="CareerTech"):
    return render_template_string(BASE_HTML, content=content_html, title=title)


# -------------------- AUTH --------------------
SIGNUP_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl font-bold mb-3">Create your CareerTech account</h2>
  <p class="text-xs text-slate-400 mb-3">Simple account to save your profile, skills and roadmap.</p>
  <input name="name" placeholder="Full Name" required class="input-box">
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn w-full">Signup</button>
  <p class="text-gray-400 mt-3 text-xs text-center">
    Already registered? <a href="/login" class="text-indigo-300 underline">Login</a>
  </p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl font-bold mb-3">Login to CareerTech</h2>
  <p class="text-xs text-slate-400 mb-3">Access your personalised B-Tech career dashboard.</p>
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn w-full">Login</button>
  <p class="text-gray-400 mt-3 text-xs text-center">
    New here? <a href="/signup" class="text-indigo-300 underline">Create account</a>
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
            return render_page("<p class='error-msg'>All fields are required.</p>" + SIGNUP_FORM, "Signup")

        db = get_db()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.close()
            return render_page("<p class='error-msg'>Email already registered. Please login.</p>" + SIGNUP_FORM, "Signup")

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

        if not ok:
            return render_page("<p class='error-msg'>Invalid email or password.</p>" + LOGIN_FORM, "Login")

        session["user"] = user.name
        session["user_id"] = user.id
        session["ai_history"] = []
        session["first_time"] = True
        return redirect("/dashboard")

    return render_page(LOGIN_FORM, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------- HOME --------------------
@app.route("/")
def home():
    logged_in = "user_id" in session

    if logged_in:
        primary_cta = '<a href="/dashboard" class="primary-cta">Open my dashboard</a>'
        subline = "Get your personalised roadmap, skills and internships in one place."
    else:
        primary_cta = '<a href="/signup" class="primary-cta">Create free student account</a>'
        subline = "Login or signup to save your roadmap and progress."

    content = f"""
    <div class="max-w-6xl mx-auto mt-4 md:mt-8 space-y-10 hero-shell">
      <!-- HERO -->
      <section class="grid md:grid-cols-2 gap-10 items-center">
        <div class="space-y-4">
          <span class="pill-badge"><span class="dot"></span>CareerTech · For serious B-Tech students</span>
          <h1 class="hero-title">
            Turn your <span class="gradient-text">B-Tech degree</span> into a real tech career.
          </h1>
          <p class="hero-sub">
            Skill roadmaps, projects, internships and an AI mentor — all tuned for Indian engineering students.
          </p>
          <div class="flex flex-wrap items-center gap-3 mt-2">
            {primary_cta}
            <a href="/chatbot" class="ghost-cta">Ask AI career doubts</a>
          </div>
          <p class="hero-footnote">{subline}</p>
        </div>

        <!-- RIGHT: Card -->
        <div class="hero-card rounded-3xl p-7 md:p-8 space-y-5">
          <p class="text-xs tracking-[0.22em] text-slate-400 uppercase">Student pass (prototype)</p>
          <div class="flex items-end gap-3">
            <span class="text-5xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-sm text-slate-300 mb-2">per student / year</span>
          </div>
          <p class="text-[13px] text-slate-300">
            One simple pass that bundles roadmaps, mentors, internships, projects and AI support for B-Tech students.
          </p>
          <ul class="text-xs text-slate-200 space-y-1.5">
            <li>• Branch-wise skill roadmaps (CSE, ECE, Mechanical, etc.)</li>
            <li>• Project ideas and final-year project support</li>
            <li>• Internship &amp; job snapshot with real tech roles</li>
            <li>• AI + human mentors for career decisions</li>
          </ul>
        </div>
      </section>

      <!-- FEATURE GRID -->
      <section class="space-y-3">
        <h3 class="section-title">CareerTech spaces</h3>
        <div class="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <a href="/courses" class="feature-card">
            🧾 Courses
            <p class="sub">Skills &amp; courses you really need.</p>
          </a>
          <a href="/colleges" class="feature-card">
            🏫 Colleges
            <p class="sub">Key engineering colleges snapshot.</p>
          </a>
          <a href="/mentors" class="feature-card">
            👨‍🏫 Mentors
            <p class="sub">Talk to working engineers.</p>
          </a>
          <a href="/jobs" class="feature-card">
            💼 Jobs &amp; Internships
            <p class="sub">Real tech roles &amp; stipends.</p>
          </a>
          <a href="/global-match" class="feature-card">
            🌍 Global Path
            <p class="sub">MS / remote / abroad options.</p>
          </a>
          <a href="/chatbot" class="feature-card">
            🤖 AI Career Mentor
            <p class="sub">Ask doubts 24×7.</p>
          </a>
        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerTech | Home")


# -------------------- DASHBOARD --------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user_name = session["user"]
    tab = request.args.get("tab", "overview")

    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserProfile(
            user_id=user_id,
            branch="",
            year="",
            skills="Python, Problem Solving, Git",
            dream_roles="Software Developer, Data Engineer",
            resume_link=""
        )
        db.add(profile)
        db.commit()

    if request.method == "POST":
        active_tab = request.form.get("tab", "overview")
        if active_tab == "profile":
            profile.branch = request.form.get("branch", "").strip()
            profile.year = request.form.get("year", "").strip()
            profile.dream_roles = request.form.get("dream_roles", "").strip()
            db.commit()
            db.close()
            return redirect("/dashboard?tab=profile")
        if active_tab == "skills":
            profile.skills = request.form.get("skills", "").strip()
            profile.resume_link = request.form.get("resume_link", "").strip()
            db.commit()
            db.close()
            return redirect("/dashboard?tab=skills")

    # refresh values
    branch = profile.branch or ""
    year = profile.year or ""
    skills = profile.skills or ""
    dream_roles = profile.dream_roles or ""
    resume_link = profile.resume_link or ""
    db.close()

    first_time = session.pop("first_time", False)
    greeting = "CareerTech welcomes you 🎉" if first_time else "Welcome back 👋"

    overview_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">{greeting}, {user_name}</h2>
        <p class="text-sm text-slate-300">
          This is your personal B-Tech career dashboard. Start by filling your branch, year,
          skills and dream roles — then ask the AI mentor for a customised roadmap.
        </p>

        <div class="grid md:grid-cols-3 gap-4 mt-4">
          <div class="dash-box">
            <p class="dash-label">Branch</p>
            <p class="dash-value">{branch or "Not set"}</p>
          </div>
          <div class="dash-box">
            <p class="dash-label">Year</p>
            <p class="dash-value">{year or "Not set"}</p>
          </div>
          <div class="dash-box">
            <p class="dash-label">Dream roles</p>
            <p class="dash-value text-sm">{dream_roles or "Example: SDE, Data Scientist, DevOps"}</p>
          </div>
        </div>

        <div class="grid md:grid-cols-2 gap-4 mt-4">
          <div class="bg-slate-900/70 border border-slate-700 rounded-2xl p-4">
            <h3 class="font-semibold mb-2 text-sm">CareerTech guidance</h3>
            <ul class="text-xs text-slate-300 space-y-1.5">
              <li>• Make one strong stack (e.g., Python + SQL + one framework).</li>
              <li>• Build 2–3 high-signal projects per role (SDE, DS, DevOps etc.).</li>
              <li>• Practice DSA for at least 30–60 mins/day.</li>
              <li>• Use internships and freelancing to prove skills.</li>
            </ul>
          </div>
          <div class="bg-slate-900/70 border border-slate-700 rounded-2xl p-4">
            <h3 class="font-semibold mb-2 text-sm">How to use this website</h3>
            <ol class="text-xs text-slate-300 space-y-1.5 list-decimal list-inside">
              <li>Fill your basic profile &amp; skills in the tabs on the left.</li>
              <li>Open <b>AI Mentor</b> from navbar or floating button and ask for a roadmap.</li>
              <li>Check <b>Courses</b>, <b>Colleges</b>, <b>Jobs</b> for ideas and targets.</li>
              <li>Iterate every month and keep updating your skills &amp; projects.</li>
            </ol>
          </div>
        </div>
      </div>
    """

    profile_panel = f"""
      <div class="space-y-4">
        <h2 class="section-title">Profile basics</h2>
        <form method="POST" class="space-y-3">
          <input type="hidden" name="tab" value="profile">
          <div>
            <label class="label">Branch</label>
            <input name="branch" class="input-box" placeholder="CSE / ECE / Mechanical / Civil / AI &amp; DS" value="{branch}">
          </div>
          <div>
            <label class="label">Year</label>
            <input name="year" class="input-box" placeholder="2nd year / 3rd year / final year" value="{year}">
          </div>
          <div>
            <label class="label">Dream roles</label>
            <textarea name="dream_roles" rows="3" class="input-box h-auto" placeholder="Example: Backend developer, Data engineer, DevOps engineer">{dream_roles}</textarea>
          </div>
          <button class="submit-btn">Save profile</button>
        </form>
      </div>
    """

    skills_panel = f"""
      <div class="space-y-4">
        <h2 class="section-title">Skills &amp; resume</h2>
        <form method="POST" class="space-y-3">
          <input type="hidden" name="tab" value="skills">
          <div>
            <label class="label">Current skills</label>
            <textarea name="skills" rows="4" class="input-box h-auto" placeholder="Example: Python, OOP, basic SQL, HTML/CSS/JS, Git, Linux">{skills}</textarea>
          </div>
          <div>
            <label class="label">Resume / portfolio link</label>
            <input name="resume_link" class="input-box" placeholder="Google Drive / GitHub / personal site link" value="{resume_link}">
          </div>
          <button class="submit-btn">Save skills</button>
        </form>
        {"<p class='text-xs text-emerald-300'>Current link: <a href='" + resume_link + "' target='_blank' class='underline'>" + resume_link + "</a></p>" if resume_link else ""}
      </div>
    """

    help_panel = """
      <div class="space-y-4">
        <h2 class="section-title">FAQ &amp; Support</h2>
        <p class="text-sm text-slate-300">
          This is a prototype built to show how a focused B-Tech career platform can look and behave.
          Data like colleges, fees, jobs and roadmaps are indicative but realistic.
        </p>
        <div class="bg-slate-900/70 border border-slate-700 rounded-2xl p-4 space-y-2 text-xs text-slate-300">
          <p><b>Is this live for payments?</b> Not yet. ₹299/year is a sample student pass for demo.</p>
          <p><b>Where do the jobs &amp; internships come from?</b> These are example roles corresponding to the current market.</p>
          <p><b>What can be added?</b> Real college integrations, company panels, verified internships and live mentor marketplace.</p>
        </div>
      </div>
    """

    base_tab = "block w-full text-left px-3 py-2 rounded-lg text-xs md:text-sm"
    def tab_cls(name):
        return base_tab + (" bg-indigo-600 text-white border border-indigo-500" if tab == name else " text-slate-300 hover:bg-slate-800 border border-transparent")

    if tab == "overview":
        panel = overview_panel
    elif tab == "profile":
        panel = profile_panel
    elif tab == "skills":
        panel = skills_panel
    else:
        panel = help_panel

    content = f"""
    <div class="max-w-6xl mx-auto">
      <div class="mb-4">
        <p class="text-xs text-slate-400">Profile · B-Tech</p>
        <h1 class="text-2xl md:text-3xl font-bold">Student dashboard</h1>
      </div>

      <div class="grid md:grid-cols-[220px,1fr] gap-6">
        <!-- SIDE TABS -->
        <aside class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 h-max">
          <p class="text-[11px] text-slate-400 mb-1">Your account</p>
          <p class="text-sm font-semibold mb-4 truncate">{user_name}</p>
          <nav class="flex flex-col gap-2">
            <a href="/dashboard?tab=overview" class="{tab_cls('overview')}">🏠 Overview</a>
            <a href="/dashboard?tab=profile" class="{tab_cls('profile')}">🧑‍🎓 Profile</a>
            <a href="/dashboard?tab=skills" class="{tab_cls('skills')}">⭐ Skills &amp; resume</a>
            <a href="/dashboard?tab=help" class="{tab_cls('help')}">❓ Help &amp; FAQ</a>
          </nav>
        </aside>

        <!-- MAIN PANEL -->
        <section class="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 md:p-6">
          {panel}
        </section>
      </div>
    </div>
    """
    return render_page(content, "Dashboard")


# -------------------- COURSES --------------------
@app.route("/courses")
def courses():
    db = get_db()
    data = db.query(Course).order_by(Course.category.asc()).all()
    db.close()

    rows = ""
    for c in data:
        rows += f"<tr><td>{c.name}</td><td>{c.category}</td></tr>"

    if not rows:
        rows = "<tr><td colspan='2'>No courses yet.</td></tr>"

    content = f"""
    <div class="max-w-5xl mx-auto">
      <h2 class="section-title mb-3">Skill-first courses for B-Tech students</h2>
      <p class="text-sm text-slate-300 mb-3">
        These are the kind of courses and tracks that actually improve hiring chances in current tech companies.
      </p>
      <table class="table mt-2">
        <tr><th>Course / Track</th><th>Best suits</th></tr>
        {rows}
      </table>
    </div>
    """
    return render_page(content, "Courses")


# -------------------- COLLEGES --------------------
@app.route("/colleges")
def colleges():
    budget = request.args.get("budget", "").strip()
    rating_min = request.args.get("rating", "").strip()
    db = get_db()
    q = db.query(College)

    if budget == "lt1":
        q = q.filter(College.fees < 100000)
    elif budget == "b1_2":
        q = q.filter(College.fees.between(100000, 200000))
    elif budget == "gt2":
        q = q.filter(College.fees > 200000)

    if rating_min:
        try:
            rv = float(rating_min)
            q = q.filter(College.rating >= rv)
        except ValueError:
            pass

    data = q.order_by(College.rating.desc()).all()
    db.close()

    rows = ""
    for col in data:
        rows += f"""
        <tr>
          <td>{col.name}</td>
          <td>{col.location}</td>
          <td>{col.branch}</td>
          <td>₹{col.fees:,}</td>
          <td>{col.rating:.1f}★</td>
        </tr>
        """
    if not rows:
        rows = "<tr><td colspan='5'>No colleges match this filter.</td></tr>"

    sel_any_b = "selected" if budget == "" else ""
    sel_lt1 = "selected" if budget == "lt1" else ""
    sel_b1_2 = "selected" if budget == "b1_2" else ""
    sel_gt2 = "selected" if budget == "gt2" else ""

    sel_any_r = "selected" if rating_min == "" else ""
    sel_40 = "selected" if rating_min == "4.0" else ""
    sel_45 = "selected" if rating_min == "4.5" else ""

    content = f"""
    <div class="max-w-6xl mx-auto">
      <h2 class="section-title mb-3">Engineering colleges snapshot (example data)</h2>
      <p class="text-sm text-slate-300 mb-4">
        Fees and ratings are indicative for demo, focused on Hyderabad / Telangana engineering colleges
        that B-Tech students commonly target.
      </p>

      <form method="GET" class="mb-4 grid md:grid-cols-3 gap-3">
        <select name="budget" class="search-bar">
          <option value="" {sel_any_b}>Any annual fees</option>
          <option value="lt1" {sel_lt1}>Below ₹1 lakh / year</option>
          <option value="b1_2" {sel_b1_2}>₹1–2 lakh / year</option>
          <option value="gt2" {sel_gt2}>Above ₹2 lakh / year</option>
        </select>

        <select name="rating" class="search-bar">
          <option value="" {sel_any_r}>Any rating</option>
          <option value="4.0" {sel_40}>4.0★ &amp; above</option>
          <option value="4.5" {sel_45}>4.5★ &amp; above</option>
        </select>

        <button class="px-3 py-2 bg-indigo-600 rounded text-sm">Filter</button>
      </form>

      <table class="table mt-2">
        <tr>
          <th>College</th>
          <th>Location</th>
          <th>Strong branches</th>
          <th>Approx. fees / year</th>
          <th>Rating</th>
        </tr>
        {rows}
      </table>
    </div>
    """
    return render_page(content, "Colleges")


# -------------------- MENTORS --------------------
@app.route("/mentors")
def mentors():
    db = get_db()
    data = db.query(Mentor).all()
    db.close()

    cards = ""
    for m in data:
        cards += f"""
        <div class="mentor-card">
          <h3 class="text-sm font-semibold mb-1">{m.name}</h3>
          <p class="text-[11px] text-indigo-300 mb-1">{m.role}</p>
          <p class="text-xs text-slate-300 mb-2">{m.experience}</p>
          <p class="text-[11px] text-emerald-300">Focus: {m.speciality}</p>
        </div>
        """

    content = f"""
    <div class="max-w-6xl mx-auto">
      <h2 class="section-title mb-3">Mentors (example profiles)</h2>
      <p class="text-sm text-slate-300 mb-4">
        These are sample mentor profiles showing the kind of people CareerTech can onboard — working engineers
        who can talk branch-wise and company-wise reality.
      </p>
      <div class="grid md:grid-cols-3 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Mentors")


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
          <h3 class="text-sm font-semibold mb-1">{j.title}</h3>
          <p class="text-[11px] text-indigo-300 mb-1">{j.company}</p>
          <p class="text-[11px] text-slate-400 mb-1">{j.location}</p>
          <p class="text-[11px] text-emerald-300 font-semibold">{j.stipend}</p>
        </div>
        """

    content = f"""
    <div class="max-w-6xl mx-auto">
      <h2 class="section-title mb-3">Jobs &amp; internship snapshot</h2>
      <p class="text-sm text-slate-300 mb-4">
        These example roles represent realistic openings for final-year B-Tech students and recent graduates.
        A real platform would plug into hiring partners and live job feeds.
      </p>
      <div class="grid md:grid-cols-3 gap-4">
        {cards}
      </div>
    </div>
    """
    return render_page(content, "Jobs & Internships")


# -------------------- GLOBAL MATCH --------------------
@app.route("/global-match")
def global_match():
    content = """
    <div class="max-w-5xl mx-auto">
      <h2 class="section-title mb-3">Global path &amp; remote-first careers</h2>
      <p class="text-sm text-slate-300 mb-4">
        CareerTech can help students explore three categories of global options:
      </p>

      <div class="grid md:grid-cols-3 gap-4">
        <div class="support-box">
          <h3 class="text-sm font-semibold mb-2">1. MS &amp; higher studies</h3>
          <ul class="text-xs text-slate-300 space-y-1.5">
            <li>• USA – MS in CS / Data / Robotics</li>
            <li>• Germany – low-tuition tech degrees</li>
            <li>• Canada – course + PR path</li>
            <li>• UK / Ireland – 1-year masters</li>
          </ul>
        </div>
        <div class="support-box">
          <h3 class="text-sm font-semibold mb-2">2. Remote-first jobs</h3>
          <ul class="text-xs text-slate-300 space-y-1.5">
            <li>• Backend / frontend engineers</li>
            <li>• Data &amp; analytics engineers</li>
            <li>• DevOps &amp; SRE roles</li>
            <li>• Freelance product engineering</li>
          </ul>
        </div>
        <div class="support-box">
          <h3 class="text-sm font-semibold mb-2">3. Exchange &amp; internships</h3>
          <ul class="text-xs text-slate-300 space-y-1.5">
            <li>• Summer research internships</li>
            <li>• Erasmus-style semester exchanges</li>
            <li>• Industry-sponsored capstone projects</li>
          </ul>
        </div>
      </div>

      <p class="text-xs text-slate-400 mt-4">
        All of this is demo content to show structure — a live product would integrate with counsellors,
        partner universities and remote-first employers.
      </p>
    </div>
    """
    return render_page(content, "Global Path")


# -------------------- AI CHATBOT --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-6">
  <h1 class="text-2xl md:text-3xl font-bold mb-1">CareerTech AI Mentor</h1>
  {% if not locked %}
    <p class="text-sm text-slate-300">
      Describe your branch, year, skills and target role. The AI mentor will respond with a concise roadmap.
      Each account currently has <b>one free long chat</b> (prototype).
    </p>
  {% else %}
    <p class="text-sm text-slate-300">
      Your free AI session is over for this demo account. You can still see the old messages below.
    </p>
  {% endif %}

  <div class="bg-slate-900/80 border border-slate-700 rounded-2xl p-4 h-[360px] overflow-y-auto">
    {% if history %}
      {% for m in history %}
        <div class="mb-3">
          {% if m.role == 'user' %}
            <div class="text-[10px] text-slate-400 mb-0.5">You</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-indigo-600 text-xs max-w-[92%]">
              {{ m.content }}
            </div>
          {% else %}
            <div class="text-[10px] text-slate-400 mb-0.5">CareerTech AI</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-slate-800 text-xs max-w-[92%]">
              {{ m.content }}
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="text-xs text-slate-400">
        👋 Start by telling me: your branch, year, college tier, current skills and what role you want (SDE / DS / DevOps etc.).
      </p>
    {% endif %}
  </div>

  {% if not locked %}
    <form method="POST" class="flex gap-2">
      <input name="message" class="input-box flex-1" autocomplete="off" placeholder="Type your question or profile..." required>
      <button class="px-4 py-2 rounded-full bg-indigo-600 text-xs font-semibold">Send</button>
    </form>
    <form method="POST" action="/chatbot/end" class="mt-2">
      <button class="text-[10px] px-3 py-1.5 rounded-full border border-rose-500/70 text-rose-200 hover:bg-rose-500/10">
        🔒 End free AI session
      </button>
    </form>
  {% else %}
    <p class="text-[10px] text-slate-400 mt-2">
      For the investor demo, this shows how AI guidance would plug into the platform.
    </p>
  {% endif %}
</div>
"""


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    locked = bool(usage and usage.used == 1)

    history = session.get("ai_history", [])
    if not isinstance(history, list):
        history = []

    if request.method == "POST":
        if locked:
            db.close()
            html = render_template_string(CHATBOT_HTML, history=history, locked=True)
            return render_page(html, "AI Mentor")

        msg = request.form.get("message", "").strip()
        if msg:
            history.append({"role": "user", "content": msg})
            messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}] + history
            client = get_groq_client()
            if client is None:
                reply = "AI is not configured yet on this server. Set GROQ_API_KEY to enable it."
            else:
                try:
                    resp = client.chat.completions.create(
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
    return render_page(html, "AI Mentor")


@app.route("/chatbot/end", methods=["POST"])
def end_chatbot():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    if usage is None:
        usage = AiUsage(user_id=user_id, used=1)
        db.add(usage)
    else:
        usage.used = 1
    db.commit()
    db.close()
    return redirect("/chatbot")


# -------------------- SUPPORT (simple) --------------------
@app.route("/support")
def support():
    content = """
    <div class="max-w-lg mx-auto">
      <h2 class="section-title mb-3">Support &amp; contact</h2>
      <p class="text-sm text-slate-300 mb-3">
        For the demo, you can explain to the investor that these are placeholder details.
        In a real launch, this would connect to WhatsApp / email / ticketing system.
      </p>
      <div class="support-box">
        <p class="text-xs">📧 support@careertech.in</p>
        <p class="text-xs">📞 +91-98xx-xxx-xxx</p>
      </div>
    </div>
    """
    return render_page(content, "Support")


if __name__ == "__main__":
    app.run(debug=True)
