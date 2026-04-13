# DevSecOps-Based Chart Validation & Objective Compliance System

A high-performance backend system built with FastAPI that automatically validates data charts (such as bar, line, and pie charts) against a set of business and structural compliance rules. This system is designed from the ground up for integration into automated DevSecOps pipelines via GitHub Actions.

---

## 🏗️ Features

* **Rule-Based Validation Engine:** Checks for data presence, allowed chart types, label consistency, objective existence, title presence, and numeric validation. 
* **Scoring System:** Outputs a score (0-100) alongside human-readable validation issues.
* **FastAPI Backend:** Fully asynchronous, self-documenting API via Swagger UI.
* **Continuous Integration:** Fully configured GitHub Actions pipeline (`build-and-test`) for linting (`flake8`) and unit testing (`pytest`).

---

## 🚀 Setup & Installation

### Prerequisites
* Python 3.10+
* Git

### 1. Clone the repository
```bash
git clone https://github.com/Helion564/chart-validation-system.git
cd chart-validation-system
```

### 2. Create and Activate a Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Running the Application

To start the local development server with live-reloading enabled, run:

**Windows System:**
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
**Linux / macOS System:**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Accessing the Local Server
Once running, you can interact with the API via your browser:
* **Root / Health Check:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Interactive API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Testing

The system includes a comprehensive Pytest suite that verifies the core validation logic and endpoint response handling. 

To run the unit tests:
```bash
pytest tests/ -v
```

To run the code linter (checks for formatting and syntax logic issues):
```bash
flake8 . --count --show-source --statistics
```

---

## 📡 API Endpoints

### `GET /`
Returns the operational status and basic information about the API service.

### `POST /validate-chart`
Accepts a JSON payload containing chart information and returns a compliance score.

**Sample Request Payload:**
```json
{
  "chart_type": "bar",
  "title": "Q1 Revenue Growth",
  "labels": ["January", "February", "March"],
  "data": [12000, 15000, 17500],
  "objective": "Demonstrate the month-over-month increase in sales revenue."
}
```

**Sample Response payload:**
```json
{
  "score": 100,
  "issues": [],
  "status": "valid"
}
```
*(Any deductions caused by invalid data types, missing labels, or unsupported formatting will reduce the output score and populate the `issues` array).*
