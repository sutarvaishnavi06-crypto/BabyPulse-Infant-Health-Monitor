from datetime import datetime
from io import BytesIO
from pathlib import Path
import sqlite3
from xml.sax.saxutils import escape

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from models.anomaly_detector import detect_anomalies

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ROOT = Path(__file__).parent
DB_PATH = ROOT / "babypulse.db"
DATA_DIR = ROOT / "datasets"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                temperature_f REAL NOT NULL,
                sleep_hours REAL NOT NULL,
                feeding_count INTEGER NOT NULL,
                wet_diapers INTEGER NOT NULL,
                heart_rate_bpm REAL,
                symptoms TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
        """)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/examples")
def examples():
    return jsonify({"datasets": sorted(p.name for p in DATA_DIR.glob("*.csv"))})


@app.get("/api/records")
def records():
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT * FROM health_records ORDER BY recorded_at DESC, id DESC LIMIT 200"
        ).fetchall()
    return jsonify({"records": [dict(row) for row in rows]})


@app.post("/api/records")
def add_record():
    data = request.get_json(silent=True) or {}
    try:
        temperature = float(data["temperature_f"])
        sleep = float(data["sleep_hours"])
        feeding = int(data["feeding_count"])
        diapers = int(data["wet_diapers"])
        heart_rate = float(data["heart_rate_bpm"]) if data.get("heart_rate_bpm") not in (None, "") else None
        recorded_at = data.get("recorded_at") or datetime.now().isoformat(timespec="minutes")
        symptoms = str(data.get("symptoms", ""))[:500]
        notes = str(data.get("notes", ""))[:1000]
        if not 80 <= temperature <= 110:
            raise ValueError("Temperature must be between 80°F and 110°F.")
        if not 0 <= sleep <= 24 or not 0 <= feeding <= 30 or not 0 <= diapers <= 30:
            raise ValueError("Please check sleep, feeding and diaper values.")
        if heart_rate is not None and not 20 <= heart_rate <= 300:
            raise ValueError("Please check the heart-rate value.")
        datetime.fromisoformat(recorded_at)
        with connect_db() as conn:
            conn.execute("""
                INSERT INTO health_records
                (recorded_at, temperature_f, sleep_hours, feeding_count,
                 wet_diapers, heart_rate_bpm, symptoms, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (recorded_at, temperature, sleep, feeding, diapers,
                  heart_rate, symptoms, notes))
        return jsonify({"message": "Health record saved."}), 201
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc) or "Please enter valid record details."}), 400


@app.post("/api/detect")
def detect():
    try:
        contamination = float(request.form.get("contamination", 0.05))
        estimators = int(request.form.get("n_estimators", 100))
        sample_name = request.form.get("sample")
        if "file" in request.files and request.files["file"].filename:
            df = pd.read_csv(request.files["file"])
            dataset_name = request.files["file"].filename
        elif sample_name:
            path = (DATA_DIR / sample_name).resolve()
            if path.parent != DATA_DIR.resolve() or not path.exists() or path.suffix.lower() != ".csv":
                return jsonify({"error": "Invalid example dataset."}), 400
            df = pd.read_csv(path)
            dataset_name = path.name
        elif request.form.get("source") == "records":
            with connect_db() as conn:
                df = pd.read_sql_query("""
                    SELECT temperature_f, sleep_hours, feeding_count,
                           wet_diapers, heart_rate_bpm
                    FROM health_records
                """, conn)
            dataset_name = "Saved daily health records"
        else:
            return jsonify({"error": "Upload a CSV, choose an example, or add daily records first."}), 400

        result = detect_anomalies(df, contamination, estimators)
        result["dataset"] = dataset_name
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not process dataset: {exc}"}), 400


@app.get("/api/report")
def report():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT recorded_at, temperature_f, sleep_hours, feeding_count,
                   wet_diapers, heart_rate_bpm, symptoms, notes
            FROM health_records ORDER BY recorded_at ASC
        """).fetchall()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="BabyPulse Health Record")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("BabyPulse - Infant Health Record Summary", styles["Title"]),
        Spacer(1, 8),
        Paragraph("A caregiver-entered record summary for discussion with a healthcare professional. "
                  "This report is not a diagnosis.", styles["BodyText"]),
        Spacer(1, 14)
    ]
    data = [["Date / time", "Temp °F", "Sleep h", "Feeds", "Wet diapers", "Heart rate"]]
    for row in rows:
        data.append([
            row["recorded_at"], f'{row["temperature_f"]:.1f}',
            f'{row["sleep_hours"]:.1f}', str(row["feeding_count"]),
            str(row["wet_diapers"]),
            "" if row["heart_rate_bpm"] is None else f'{row["heart_rate_bpm"]:.0f}'
        ])
    if len(data) == 1:
        data.append(["No records entered", "", "", "", "", ""])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9e7ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#302b60")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7d8e4")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP")
    ]))
    story.extend([table, Spacer(1, 12), Paragraph("Caregiver notes and symptoms", styles["Heading2"])])
    for row in rows:
        detail = f'<b>{escape(row["recorded_at"])}</b> — {escape(row["symptoms"] or "No symptoms entered")}. {escape(row["notes"])}'
        story.append(Paragraph(detail, styles["BodyText"]))
        story.append(Spacer(1, 5))
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name="BabyPulse_Health_Report.pdf")


init_db()

if __name__ == "__main__":
    app.run(debug=True)
