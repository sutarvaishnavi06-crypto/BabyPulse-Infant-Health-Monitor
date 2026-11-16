# BabyPulse — Infant Health Pattern Monitor

BabyPulse is a small Flask web application for recording everyday infant health observations, exploring the history, and using Scikit-learn Isolation Forest to flag unusual numerical patterns. Plotly.js displays the model results interactively.

## Assignment alignment

The assignment requires a general-purpose interactive anomaly-detection system. BabyPulse implements this workflow using infant health records as its practical application domain. The underlying anomaly-detection engine is not limited to healthcare and can be reused with suitable numerical datasets from other domains. The healthcare theme is the application's use case, while the required Isolation Forest algorithm, configurable parameters, CSV upload, anomaly scores, classification labels and interactive visualisation remain the core implementation.

## Features

- Record daily temperature, sleep, feeding count, wet diapers, optional heart rate, symptoms and caregiver notes.
- Store and review entries locally using SQLite.
- Upload CSV data or choose a built-in example dataset.
- Configure Isolation Forest contamination and number of estimators.
- View anomaly labels, anomaly scores, summary metrics and Plotly.js scatter plots.
- Re-run detection without refreshing the page.
- Export saved entries as a concise PDF report for discussion with a healthcare professional.

## Technology

Python, Flask, pandas, NumPy, Scikit-learn, SQLite, HTML5, CSS3, JavaScript, Plotly.js and ReportLab.

## Requirements

- Python 3.10 or newer
- pip

## Run locally

1. Extract the ZIP and open the `BabyPulse` folder in a terminal.
2. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

3. Activate it:

   **Windows PowerShell**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   **Windows Command Prompt**
   ```cmd
   venv\Scripts\activate
   ```

   **macOS/Linux**
   ```bash
   source venv/bin/activate
   ```

4. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   python app.py
   ```

6. Open http://127.0.0.1:5000 in your browser.

## How to use

- Add daily observations in the Daily Health Entry form; saved records are stored in `babypulse.db`.
- For anomaly detection, use at least five saved records, upload a CSV, or select an example dataset.
- CSV files need at least five rows and two usable numeric columns. The model uses all usable numeric columns; the scatter plot displays the first two.
- Adjust contamination (0.01–0.50) and estimators (10–500), then select **Run detection**.
- Download the PDF report to review saved entries.

## Understanding the model output

Scikit-learn Isolation Forest returns `1` for a normal observation and `-1` for an anomaly. The displayed anomaly score is the negative decision function; larger values indicate observations the model considers more unusual. It is not a probability. Contamination is a model setting that influences the expected proportion of outliers, not a clinical threshold or proof of illness.

## Deployment

The included `Procfile` uses Gunicorn. On a Python-compatible cloud host:

1. Push the project to a Git repository.
2. Create a Python web service.
3. Set the install/build command to `pip install -r requirements.txt`.
4. Set the start command to `gunicorn app:app`.
5. Deploy and open the service URL.

For a persistent deployment, configure persistent storage for `babypulse.db`; an ephemeral filesystem may reset saved records on redeployment. Plotly.js is loaded from a CDN, so the browser needs internet access for the chart library.

## Safety and privacy note

BabyPulse is an educational prototype for record keeping and statistical exploration. It is not a medical device and does not diagnose, predict illness, assess urgency or recommend treatment. An anomaly flag is not a diagnosis, and no flag does not mean an infant is well. Follow local clinical guidance and consult a qualified healthcare professional for health concerns; urgent symptoms require prompt medical care regardless of model output. Use synthetic or de-identified data for demonstrations. Do not upload identifiable infant health information to an unsecured deployment.

## Project structure

```text
BabyPulse/
├── app.py
├── requirements.txt
├── Procfile
├── README.md
├── babypulse.db              # created automatically at first run
├── models/
│   ├── __init__.py
│   └── anomaly_detector.py
├── datasets/
│   ├── sample_infant_health.csv
│   └── sample_daily_records.csv
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/dashboard.js
```
