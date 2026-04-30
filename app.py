"""
============================================================
NATIONAL SCHEME FRAUD PORTAL — NSFP v2.0
app.py | Developed by Sona Choudhary | 2026
AI-Powered Government Beneficiary Fraud Detection
============================================================
"""

import os
import random
import hashlib
import logging

from flask import (
    Flask, render_template, request,
    redirect, session, send_file, url_for
)
import mysql.connector
from mysql.connector import errorcode
import pandas as pd
import joblib
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine
from urllib.parse import quote_plus, unquote, urlparse
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score
)
from sklearn.model_selection import train_test_split

# ─── LOGGING ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("NSFP")

# ─── CONFIGURATION ──────────────────────────────────────────
def load_database_config():
    """Read database settings from local env vars or Railway MySQL variables."""
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("MYSQL_URL")
        or os.getenv("MYSQL_PUBLIC_URL")
    )

    if database_url:
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or "root"),
            "password": unquote(parsed.password or ""),
            "database": (parsed.path or "/gov_ai_fraud").lstrip("/"),
        }

    return {
        "host": os.getenv("DB_HOST") or os.getenv("MYSQLHOST") or "localhost",
        "port": int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"),
        "user": os.getenv("DB_USER") or os.getenv("MYSQLUSER") or "root",
        "password": os.getenv("DB_PASS") or os.getenv("MYSQLPASSWORD") or "root@123",
        "database": os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE") or "gov_ai_fraud",
    }


DB_CONFIG = load_database_config()
DEFAULT_ADMIN_USERNAME = "sona2026"
DEFAULT_ADMIN_PASSWORD = "Papa9829"


class Config:
    DB_HOST   = DB_CONFIG["host"]
    DB_PORT   = DB_CONFIG["port"]
    DB_USER   = DB_CONFIG["user"]
    DB_PASS   = DB_CONFIG["password"]
    DB_NAME   = DB_CONFIG["database"]
    SECRET    = os.getenv("SECRET_KEY","nsfp_gov_secret_2026_sona")
    REPORTS_DIR = "reports"
    STATIC_DIR = "static"
    DATA_PATH = "fraud_output.csv"
    MODEL_PATH = "fraud_model.pkl"

# ─── FLASK APP ───────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = Config.SECRET
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Ensure reports directory exists
os.makedirs(Config.REPORTS_DIR, exist_ok=True)
os.makedirs(Config.STATIC_DIR, exist_ok=True)

# ─── DATABASE ────────────────────────────────────────────────
def get_db():
    """Return a fresh MySQL connection."""
    try:
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME,
            connection_timeout=10,
        )
    except mysql.connector.Error as e:
        if e.errno != errorcode.ER_BAD_DB_ERROR:
            raise

        setup_db = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            connection_timeout=10,
        )
        setup_cur = setup_db.cursor()
        setup_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        setup_cur.close()
        setup_db.close()

        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME,
            connection_timeout=10,
        )


def column_exists(cur, table_name, column_name):
    """Return whether a column exists in the configured database."""
    cur.execute("""
        SELECT COUNT(*) AS col_count
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
          AND column_name = %s
    """, (Config.DB_NAME, table_name, column_name))
    row = cur.fetchone()
    return row[0] > 0


def ensure_column(cur, table_name, column_name, column_definition):
    """Add a missing column without disturbing existing data."""
    if not column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition}")


def ensure_database_schema(db):
    """Create the small app schema if Railway MySQL starts empty."""
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS states (
            state_id INT AUTO_INCREMENT PRIMARY KEY,
            state_name VARCHAR(100) NOT NULL,
            state_code VARCHAR(5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_state_name (state_name)
        ) ENGINE=InnoDB
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            admin_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL
        ) ENGINE=InnoDB
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            aadhaar BIGINT NOT NULL,
            age TINYINT UNSIGNED NOT NULL,
            income INT UNSIGNED NOT NULL,
            schemes_taken TINYINT UNSIGNED NOT NULL DEFAULT 0,
            fraud_predicted TINYINT(1) NOT NULL DEFAULT 0,
            confidence_score FLOAT,
            state_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (state_id) REFERENCES states(state_id) ON DELETE RESTRICT,
            INDEX idx_fraud (fraud_predicted),
            INDEX idx_state (state_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            admin_user VARCHAR(50),
            action VARCHAR(100),
            details TEXT,
            ip_address VARCHAR(45),
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (admin_user),
            INDEX idx_time (logged_at)
        ) ENGINE=InnoDB
    """)

    ensure_column(cur, "states", "state_code", "VARCHAR(5)")
    ensure_column(cur, "states", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ensure_column(cur, "admin_users", "full_name", "VARCHAR(100)")
    ensure_column(cur, "admin_users", "last_login", "TIMESTAMP NULL")
    ensure_column(cur, "beneficiaries", "confidence_score", "FLOAT")
    ensure_column(cur, "beneficiaries", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ensure_column(cur, "beneficiaries", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

    states = [
        ("Rajasthan", "RJ"),
        ("Uttar Pradesh", "UP"),
        ("Madhya Pradesh", "MP"),
        ("Delhi", "DL"),
        ("Bihar", "BR"),
        ("Haryana", "HR"),
        ("Gujarat", "GJ"),
        ("Karnataka", "KA"),
    ]
    cur.executemany("""
        INSERT INTO states (state_name, state_code)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE state_code = VALUES(state_code)
    """, states)
    cur.execute("""
        INSERT INTO admin_users (username, password_hash, full_name)
        VALUES (%s, SHA2(%s, 256), %s)
        ON DUPLICATE KEY UPDATE
            password_hash = VALUES(password_hash),
            full_name = VALUES(full_name)
    """, (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, "Sona Choudhary"))
    db.commit()
    cur.close()


def beneficiaries_has_created_at(cur):
    """Return whether the live beneficiaries table has a created_at column."""
    cur.execute("""
        SELECT COUNT(*) AS col_count
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = 'beneficiaries'
          AND column_name = 'created_at'
    """, (Config.DB_NAME,))
    row = cur.fetchone()
    if isinstance(row, dict):
        return row["col_count"] > 0
    return row[0] > 0


def beneficiary_created_at_select(cur):
    return "b.created_at" if beneficiaries_has_created_at(cur) else "NULL AS created_at"

# SQLAlchemy engine for pandas read_sql
_db_url = (
    f"mysql+mysqlconnector://{quote_plus(Config.DB_USER)}:"
    f"{quote_plus(Config.DB_PASS)}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
)
engine = create_engine(_db_url, pool_pre_ping=True)

# ─── AI MODEL ────────────────────────────────────────────────
try:
    model = joblib.load(Config.MODEL_PATH)
    logger.info("✅ AI model loaded successfully.")
except Exception as e:
    logger.error(f"❌ Failed to load model: {e}")
    model = None


def load_chart_fonts():
    try:
        return (
            ImageFont.truetype("arialbd.ttf", 28),
            ImageFont.truetype("arial.ttf", 18),
            ImageFont.truetype("arialbd.ttf", 46),
        )
    except OSError:
        return (ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default())


def draw_centered_text(draw, box, text, font, fill):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = left + ((right - left) - text_w) / 2
    y = top + ((bottom - top) - text_h) / 2
    draw.text((x, y), text, font=font, fill=fill)


def blend_rgb(start, end, amount):
    return tuple(round(start[i] + (end[i] - start[i]) * amount) for i in range(3))


def generate_accuracy_artifacts(force=False):
    """Create model metric charts from fraud_output.csv and return metric values."""
    chart_paths = {
        "confusion_matrix": os.path.join(Config.STATIC_DIR, "confusion_matrix.png"),
        "accuracy_chart": os.path.join(Config.STATIC_DIR, "accuracy_chart.png"),
    }
    metrics_path = os.path.join(Config.STATIC_DIR, "model_metrics.json")

    if not force and os.path.exists(metrics_path) and all(os.path.exists(path) for path in chart_paths.values()):
        try:
            return pd.read_json(metrics_path, typ="series").to_dict()
        except Exception:
            logger.warning("Could not read cached model metrics; regenerating charts.")

    df = pd.read_csv(Config.DATA_PATH)
    df.columns = df.columns.str.lower().str.strip()

    features = ["age", "income", "schemes_taken"]
    label = "fraud_predicted"
    X = df[features]
    y = df[label]

    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )

    trained_model = IsolationForest(
        n_estimators=200,
        contamination=0.2,
        max_samples="auto",
        random_state=42,
        n_jobs=1,
    )
    trained_model.fit(X_train)
    joblib.dump(trained_model, Config.MODEL_PATH)

    raw_preds = trained_model.predict(X_test)
    preds = [1 if pred == -1 else 0 for pred in raw_preds]

    metric_values = {
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
    }
    pd.Series(metric_values).to_json(metrics_path)

    cm = confusion_matrix(y_test, preds, labels=[0, 1])
    title_font, label_font, value_font = load_chart_fonts()
    matrix_img = Image.new("RGB", (900, 620), "#0b1528")
    draw = ImageDraw.Draw(matrix_img)
    draw_centered_text(draw, (0, 28, 900, 70), "Confusion Matrix - IsolationForest", title_font, "#FFD700")
    draw_centered_text(draw, (245, 96, 780, 125), "Predicted Label", label_font, "#aabbcc")
    draw.text((42, 300), "True Label", fill="#aabbcc", font=label_font)

    labels = ["Genuine", "Fraud"]
    cell = 180
    start_x = 280
    start_y = 190
    max_value = max(int(cm.max()), 1)
    for idx, label_text in enumerate(labels):
        draw_centered_text(draw, (start_x + idx * cell, 145, start_x + (idx + 1) * cell, 175), label_text, label_font, "#aabbcc")
        draw_centered_text(draw, (130, start_y + idx * cell, 255, start_y + (idx + 1) * cell), label_text, label_font, "#aabbcc")

    for row in range(2):
        for col in range(2):
            value = int(cm[row, col])
            intensity = value / max_value
            color = blend_rgb((255, 246, 173), (239, 68, 68), intensity)
            x1 = start_x + col * cell
            y1 = start_y + row * cell
            x2 = x1 + cell
            y2 = y1 + cell
            draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=color, outline="#1e3a5f", width=3)
            draw_centered_text(draw, (x1, y1, x2, y2), str(value), value_font, "#111827")

    matrix_img.save(chart_paths["confusion_matrix"])

    metric_labels = ["Accuracy", "Precision", "Recall", "F1 Score"]
    values = [metric_values["accuracy"], metric_values["precision"], metric_values["recall"], metric_values["f1"]]
    colors = ["#3b82f6", "#22c55e", "#f97316", "#FFD700"]
    chart_img = Image.new("RGB", (980, 560), "#0b1528")
    draw = ImageDraw.Draw(chart_img)
    draw_centered_text(draw, (0, 28, 980, 70), "Model Evaluation Metrics", title_font, "#FFD700")
    left, top, right, bottom = 115, 115, 910, 450
    draw.line((left, bottom, right, bottom), fill="#1e3a5f", width=3)
    draw.line((left, top, left, bottom), fill="#1e3a5f", width=3)
    for i in range(6):
        y_pos = bottom - i * (bottom - top) / 5
        draw.line((left, y_pos, right, y_pos), fill="#182b49", width=1)
        draw.text((52, y_pos - 10), f"{i * 20}%", fill="#aabbcc", font=label_font)

    bar_width = 96
    gap = (right - left - (bar_width * 4)) / 5
    for idx, (label_text, value, color) in enumerate(zip(metric_labels, values, colors)):
        x1 = left + gap + idx * (bar_width + gap)
        x2 = x1 + bar_width
        y1 = bottom - value * (bottom - top)
        draw.rounded_rectangle((x1, y1, x2, bottom), radius=8, fill=color)
        draw_centered_text(draw, (x1 - 30, bottom + 18, x2 + 30, bottom + 50), label_text, label_font, "#aabbcc")
        draw_centered_text(draw, (x1 - 20, y1 - 34, x2 + 20, y1 - 8), f"{value:.1%}", label_font, "#ffffff")

    chart_img.save(chart_paths["accuracy_chart"])

    global model
    model = trained_model
    logger.info("Accuracy charts generated automatically.")
    return metric_values


def ensure_model_ready():
    """Load or regenerate the model before prediction."""
    global model
    if model is not None:
        return True

    if not os.path.exists(Config.DATA_PATH):
        return False

    try:
        generate_accuracy_artifacts(force=True)
    except Exception as e:
        logger.error(f"Model regeneration failed: {e}")
        return False

    return model is not None


def state_exists(state_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT 1 FROM states WHERE state_id = %s LIMIT 1", (state_id,))
        exists = cur.fetchone() is not None
        cur.close()
        db.close()
        return exists
    except Exception as e:
        logger.error(f"State validation error: {e}")
        return False

# ─── AUTH DECORATOR ──────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# ─── ROUTES ──────────────────────────────────────────────────

@app.route("/")
def login_page():
    if "admin" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "admin" in session:
            return redirect(url_for("dashboard"))
        return render_template("login.html")
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("login.html", error="Please fill in all fields.")

    try:
        db  = get_db()
        ensure_database_schema(db)
        cur = db.cursor()
        cur.execute(
            "SELECT password_hash FROM admin_users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        cur.close()
        db.close()
    except Exception as e:
        logger.error(f"DB error on login: {e}")
        return render_template("login.html", error="Database connection error. Try again.")

    if row:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if hashed == row[0]:
            session["admin"]    = username
            session.permanent   = True
            logger.info(f"Login success: {username}")
            return redirect(url_for("dashboard"))

    logger.warning(f"Failed login attempt for: {username}")
    return render_template("login.html", error="Invalid username or password.")


@app.route("/dashboard")
@login_required
def dashboard():
    result = request.args.get('result', '')
    states = []
    data = []
    try:
        db  = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM states ORDER BY state_name")
        states = cur.fetchall()

        created_at_select = beneficiary_created_at_select(cur)
        order_clause = "ORDER BY b.created_at DESC" if created_at_select == "b.created_at" else "ORDER BY b.id DESC"

        cur.execute(f"""
            SELECT
                b.id,
                b.aadhaar,
                b.age,
                b.income,
                b.schemes_taken,
                b.fraud_predicted,
                s.state_name AS location,
                {created_at_select}
            FROM beneficiaries b
            LEFT JOIN states s ON b.state_id = s.state_id
            {order_clause}
        """)
        data = cur.fetchall()

        cur.close()
        db.close()
    except Exception as e:
        logger.error(f"Dashboard DB error: {e}")

    df      = pd.DataFrame(data)
    total   = len(df)
    fraud   = int(df["fraud_predicted"].sum()) if total > 0 else 0
    genuine = total - fraud

    table_html = df.to_html(
        classes="table", index=False, border=0
    ) if total > 0 else "<p style='padding:20px;color:var(--text-muted);'>No records yet.</p>"

    return render_template(
        "dashboard.html",
        total=total,
        fraud=fraud,
        genuine=genuine,
        tables=table_html,
        states=states,
        result=result,
    )


@app.route("/predict", methods=["POST"])
@login_required
def predict():
    if not ensure_model_ready():
        return redirect(url_for("dashboard") + "?result=Model+not+loaded")

    try:
        age      = int(request.form["age"])
        income   = int(request.form["income"])
        schemes  = int(request.form["schemes"])
        state_id = int(request.form["state"])
    except (ValueError, KeyError):
        return redirect(url_for("dashboard") + "?result=Invalid+input+data")

    if not (1 <= age <= 120):
        return redirect(url_for("dashboard") + "?result=Invalid+age+value")
    if not (0 <= income <= 100000000):
        return redirect(url_for("dashboard") + "?result=Invalid+income+value")
    if not (0 <= schemes <= 100):
        return redirect(url_for("dashboard") + "?result=Invalid+schemes+value")
    if not state_exists(state_id):
        return redirect(url_for("dashboard") + "?result=Invalid+state+selected")

    # AI Prediction
    features = pd.DataFrame([{
        "age": age,
        "income": income,
        "schemes_taken": schemes,
    }])
    raw_pred = model.predict(features)[0]
    pred     = 1 if raw_pred == -1 else 0

    # Random Aadhaar (demo — replace with real Aadhaar input in production)
    aadhaar  = random.randint(100000000000, 999999999999)

    try:
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO beneficiaries
               (aadhaar, age, income, schemes_taken, fraud_predicted, state_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (aadhaar, age, income, schemes, pred, state_id)
        )
        db.commit()
        cur.close()
        db.close()
        logger.info(f"Prediction: age={age}, income={income}, schemes={schemes}, fraud={pred}")
    except Exception as e:
        logger.error(f"Predict DB insert error: {e}")
        return redirect(url_for("dashboard") + "?result=Could+not+save+prediction")

    result_msg = "FRAUD DETECTED — Flagged for review" if pred == 1 else "GENUINE BENEFICIARY — Cleared by AI"
    return redirect(url_for("dashboard") + f"?result={quote_plus(result_msg)}")


@app.route("/heatmap")
@login_required
def heatmap():
    try:
        df = pd.read_sql("""
            SELECT
                s.state_name,
                COUNT(*) AS fraud_cases
            FROM beneficiaries b
            JOIN states s ON b.state_id = s.state_id
            WHERE b.fraud_predicted = 1
            GROUP BY s.state_name
            ORDER BY fraud_cases DESC
        """, engine)
        table_html = df.to_html(
            classes="table", index=False, border=0
        )
    except Exception as e:
        logger.error(f"Heatmap error: {e}")
        table_html = "<p style='padding:20px;color:var(--text-muted);'>No data available.</p>"

    return render_template("heatmap.html", table=table_html)


@app.route("/accuracy")
@login_required
def accuracy():
    try:
        metrics = generate_accuracy_artifacts()
        chart_version = int(max(
            os.path.getmtime(os.path.join(Config.STATIC_DIR, "confusion_matrix.png")),
            os.path.getmtime(os.path.join(Config.STATIC_DIR, "accuracy_chart.png")),
        ))
        error = ""
    except Exception as e:
        logger.error(f"Accuracy artifact generation error: {e}")
        metrics = {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}
        chart_version = 0
        error = "Unable to generate model charts. Check fraud_output.csv and dependencies."

    metric_percentages = {
        key: round(value * 100)
        for key, value in metrics.items()
    }
    return render_template(
        "accuracy.html",
        metrics=metric_percentages,
        chart_version=chart_version,
        error=error,
    )


@app.route("/report")
@login_required
def report():
    try:
        db  = get_db()
        cur = db.cursor(dictionary=True)
        created_at_select = beneficiary_created_at_select(cur)
        order_clause = "ORDER BY b.created_at DESC" if created_at_select == "b.created_at" else "ORDER BY b.id DESC"
        cur.execute(f"""
            SELECT
                b.id,
                b.aadhaar,
                b.age,
                b.income,
                b.schemes_taken,
                b.fraud_predicted,
                s.state_name AS location,
                {created_at_select}
            FROM beneficiaries b
            LEFT JOIN states s ON b.state_id = s.state_id
            {order_clause}
        """)
        df = pd.DataFrame(cur.fetchall())
        cur.close()
        db.close()
    except Exception as e:
        logger.error(f"Report DB error: {e}")
        return "Database error while generating report.", 500

    pdf = FPDF()
    pdf.add_page()

    # ── Header
    pdf.set_fill_color(0, 33, 71)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 215, 0)
    pdf.cell(0, 12, "NATIONAL SCHEME FRAUD PORTAL", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(0, 8, "Government of India | AI-Powered Fraud Detection Report", ln=True, align="C")
    pdf.ln(10)

    # ── Summary
    total   = len(df)
    fraud   = int(df["fraud_predicted"].sum()) if total > 0 else 0
    genuine = total - fraud

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(60, 7, f"Total Beneficiaries: {total}", ln=False)
    pdf.cell(60, 7, f"Fraud Detected: {fraud}", ln=False)
    pdf.cell(0, 7, f"Genuine: {genuine}", ln=True)
    pdf.ln(4)

    # ── Table header
    cols = ["ID", "Aadhaar", "Age", "Income", "Schemes", "Fraud", "Location", "Created At"]
    widths = [12, 40, 12, 22, 18, 14, 18, 40]

    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(0, 33, 71)
    pdf.set_text_color(255, 255, 255)
    for col, w in zip(cols, widths):
        pdf.cell(w, 7, col, border=1, fill=True)
    pdf.ln()

    # ── Table rows
    pdf.set_font("Arial", "", 7)
    pdf.set_text_color(0, 0, 0)

    for _, row in df.iterrows():
        fill = False
        if int(row.get("fraud_predicted", 0)) == 1:
            pdf.set_fill_color(255, 230, 230)
            fill = True
        else:
            pdf.set_fill_color(240, 255, 240)
            fill = True

        row_vals = [
            str(row.get("id", "")),
            str(row.get("aadhaar", "")),
            str(row.get("age", "")),
            str(row.get("income", "")),
            str(row.get("schemes_taken", "")),
            "FRAUD" if int(row.get("fraud_predicted", 0)) == 1 else "OK",
            str(row.get("location", "")),
            str(row.get("created_at", ""))[:16],
        ]
        for val, w in zip(row_vals, widths):
            pdf.cell(w, 6, val[:20], border=1, fill=fill)
        pdf.ln()

    # ── Footer
    pdf.ln(6)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "© 2026 National Scheme Fraud Portal | Developed by Sona Choudhary | NSFP v2.0", ln=True, align="C")

    report_path = os.path.join(Config.REPORTS_DIR, "gov_report.pdf")
    pdf.output(report_path)
    logger.info("Report generated successfully.")
    return send_file(report_path, as_attachment=True, download_name="NSFP_Fraud_Report_2026.pdf")


@app.route("/logout")
def logout():
    admin = session.get("admin", "unknown")
    session.clear()
    logger.info(f"Logout: {admin}")
    return redirect(url_for("login_page"))


# ─── ERROR HANDLERS ──────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("login.html", error="Page not found (404)"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("login.html", error="Internal server error. Please try again."), 500


# ─── RUN ─────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
