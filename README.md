# 🚆 AI Automatic Railway Block Planner

An AI-powered railway maintenance planning and dynamic re-planning system that automatically analyzes maintenance tasks, railway assets, train movements, conflicts, and operational risks to generate optimized maintenance blocks with minimal impact on train operations.

## 📌 Problem Statement

Railway maintenance activities across Engineering, Traction Distribution, and Signal & Telecommunication departments are often planned independently.

This can lead to:

- Poor coordination between departments
- Inefficient utilization of maintenance blocks
- Conflicts with train operations
- Increased asset downtime
- Manual and time-consuming scheduling
- Difficulty responding quickly to unexpected operational events

The system aims to provide an integrated and intelligent platform for automatic block planning, conflict detection, optimization, and real-time re-planning.

## 💡 Solution

The AI Automatic Railway Block Planner integrates maintenance tasks, railway assets, defects, train schedules, and operational events into a centralized planning system.

The platform:

1. Collects maintenance and railway network data.
2. Calculates maintenance priority and asset risk.
3. Generates maintenance blocks.
4. Analyzes train-block conflicts.
5. Detects affected trains and conflict duration.
6. Suggests alternative safe maintenance windows.
7. Automatically re-plans blocks after operational events.
8. Supports the complete maintenance workflow from planning to completion.
9. Provides AI-powered recommendations and operational insights.

## ⭐ Key Features

### 🛠️ Automatic Maintenance Block Planning

Creates maintenance blocks based on maintenance tasks, railway sections, schedules, and operational constraints.

### ⚠️ Conflict Detection

Automatically detects conflicts between maintenance blocks and train movements.

### 🚆 Train Impact Analysis

Identifies affected trains, conflict duration, impact level, and recommended actions.

### 🔄 Dynamic Re-Planning

When a train delay or operational event occurs, the system recalculates the maintenance plan and recommends a safer alternative window.

### 🤖 AI Risk Analysis

Evaluates asset criticality, defects, maintenance tasks, and operational conditions to calculate risk levels.

### 🧠 AI Decision Engine

Generates intelligent maintenance decisions such as:

- URGENT
- HIGH
- MEDIUM
- LOW

### 🎯 Smart Maintenance Priority

Ranks maintenance activities using priority and operational risk factors.

### 🏆 AI Best Maintenance Plan

Identifies the best available maintenance task/plan based on AI planning scores and operational conditions.

### 👨‍💼 AI Operations Agent

Provides system-level operational analysis, recommendations, and intelligent maintenance guidance.

### 💬 AI Operations Q&A

Users can ask operational questions such as:

- Why is a maintenance task urgent?
- What is the current system status?
- Are there any train delays?
- What is the best maintenance plan?

### 📅 Railway Scheduling Timeline

Provides a visual timeline of maintenance blocks and train movements.

### 🔧 Maintenance Workflow

Supports:

`PLANNED → APPROVED → IN_PROGRESS → COMPLETED`

with cancellation and re-planning support.

### 📊 Admin Analytics

Provides operational KPIs, maintenance statistics, AI risk analytics, block analytics, and visual charts.

## 🔄 AI / Optimization Workflow

```text
Maintenance Tasks
        ↓
Asset & Defect Analysis
        ↓
Priority Calculation
        ↓
Maintenance Block Generation
        ↓
Train Conflict Detection
        ↓
Train Impact Analysis
        ↓
AI Decision & Optimization
        ↓
Safe Maintenance Window
        ↓
Dynamic Re-Planning
        ↓
Apply Re-Plan
        ↓
Operational Execution
        ↓
Completion
🚨 Dynamic Re-Planning Example

A train delay can trigger the following workflow:

Train Delay Detected
        ↓
Conflict Identified
        ↓
Affected Train Detected
        ↓
Alternative Window Calculated
        ↓
Re-Plan Generated
        ↓
Re-Plan Applied
        ↓
Maintenance Block Updated
        ↓
Operational Event Resolved

Example:

Original Block:
10:00 – 10:45

Detected Train Conflict:
Train 1

Recommended Alternative:
08:00 – 08:45

Result:
Block re-planned successfully
🧠 AI Risk Example

The system evaluates:

Asset criticality
Open defects
Defect severity
Active maintenance tasks
Operational conditions

Example critical-risk asset:

Asset: SG001
Type: SIGNAL
Criticality: CRITICAL
Risk Score: 90
Risk Level: CRITICAL
Open Defects: 1

The AI Operations Agent can therefore raise an urgent operational recommendation.

🛠️ Tech Stack
Backend
Python
FastAPI
SQLAlchemy
PostgreSQL
Pandas
Pydantic
Uvicorn
Frontend
React
Vite
JavaScript
CSS
Recharts
Database
PostgreSQL
🏗️ System Architecture
                    ┌─────────────────────────┐
                    │      React Frontend     │
                    │   Railway Dashboard     │
                    └────────────┬────────────┘
                                 │
                                 │ REST API
                                 ↓
                    ┌─────────────────────────┐
                    │      FastAPI Backend    │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ↓                      ↓                      ↓
 ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
 │ Planning Engine│    │ AI Engines     │    │ Analytics      │
 │ Block Planner  │    │ Risk / Agent   │    │ Engine         │
 │ Optimization   │    │ Decision       │    │                │
 └────────────────┘    └────────────────┘    └────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │      PostgreSQL DB      │
                    └─────────────────────────┘
📁 Project Structure
railway-block-planner/
│
├── backend/
│   ├── data/
│   │   ├── assets.csv
│   │   ├── defects.csv
│   │   ├── goods_forecast.csv
│   │   ├── sections.csv
│   │   ├── smms_tasks.csv
│   │   ├── stations.csv
│   │   ├── tdms_tasks.csv
│   │   ├── tms_tasks.csv
│   │   ├── train_schedule.csv
│   │   └── trains.csv
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── schema.sql
│   │
│   ├── engines/
│   │   ├── ai_agent.py
│   │   ├── ai_decision_engine.py
│   │   ├── ai_planner.py
│   │   ├── analytics_engine.py
│   │   ├── block_planner.py
│   │   ├── optimization_engine.py
│   │   ├── priority_engine.py
│   │   └── risk_engine.py
│   │
│   ├── app.py
│   └── seed_data.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── .gitignore
├── requirements.txt
└── README.md
⚙️ How to Run Locally
1. Clone the repository
git clone https://github.com/Abhiraj07-07/railway-block-planner.git
cd railway-block-planner
2. Create Python virtual environment
python -m venv .venv

Activate on Windows:

.venv\Scripts\activate
3. Install backend dependencies
pip install -r requirements.txt
4. Configure PostgreSQL

Create a PostgreSQL database:

railway_block_planner

Then configure the database connection according to the backend configuration.

5. Initialize database

Use the SQL schema located at:

backend/database/schema.sql
6. Seed initial data
python backend/seed_data.py
7. Start backend

From the project root:

uvicorn backend.app:app --reload

Backend:

http://127.0.0.1:8000

Swagger API documentation:

http://127.0.0.1:8000/docs
8. Start frontend

Open a second terminal:

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173
🔌 API

FastAPI automatically provides interactive API documentation at:

http://127.0.0.1:8000/docs

Important API capabilities include:

Maintenance block management
Operational event creation
Conflict analysis
Dynamic re-planning
AI risk analysis
AI decision analysis
AI Operations Agent
Analytics
Train impact analysis
🧪 Demonstrated End-to-End Scenario

The system has been tested with the following operational workflow:

Create Maintenance Block
        ↓
Detect Train Conflict
        ↓
Analyze Train Impact
        ↓
Generate AI Re-Plan
        ↓
Apply Re-Plan
        ↓
Update Maintenance Window
        ↓
Approve Block
        ↓
Start Maintenance
        ↓
Complete Block

Example successful re-planning:

Block:
BLK-20260828-006

Original Window:
10:00 – 10:45

Alternative Window:
08:00 – 08:45

Result:
Re-planned successfully
📊 Dashboard Modules

The dashboard provides:

Executive Management Summary
Operations Control Center
AI Operations Agent
AI Operations Q&A
Railway Network
Maintenance Tasks
Defect Monitoring
Train Schedule
Scheduling Timeline
Train Impact & Rescheduling
Maintenance Plan Optimization
AI Risk Distribution
AI Decision Analytics
Admin Analytics
🔮 Future Scope

Potential future enhancements include:

Real-time railway control-room data integration
SMS / alert notifications
Live train tracking
Automatic event ingestion
Advanced machine-learning based prediction
Multi-zone railway network scaling
Role-based access control
Cloud deployment
Advanced simulation and what-if planning
Integration with enterprise railway maintenance systems
🎯 Project Goal

The goal of the system is to make railway maintenance planning:

Faster • Smarter • Safer • Coordinated • Data-Driven

while reducing maintenance conflicts and minimizing disruption to train operations.

👥 Project

AI Automatic Railway Block Planner
