# Clovio - AI-Powered Academic Collaboration Platform

Clovio is an AI-powered academic collaboration platform designed specifically for university students and instructors to transform group projects from chaotic experiences into structured, fair, and productive teamwork.

## Features

- **AI-Powered Task Distribution**: Intelligent matching of student skills with project requirements
- **Real-Time Progress Tracking**: Monitor project progress and task completion
- **Automated Coordination**: Scheduling, document management, and team chat
- **Academic Oversight**: Professor dashboards, contribution visibility, and learning analytics
- **Skill Development Tracking**: Monitor skill growth and learning outcomes
- **Fair Workload Distribution**: Ensure equal contribution across team members

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy** - ORM for database operations
- **JWT** - Authentication and authorization
- **OpenAI API** - AI-powered task breakdown and assignment
- **WebSocket** - Real-time communication support

### Frontend
- **React 18** - Modern UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first CSS framework
- **Zustand** - State management
- **React Query** - Data fetching and caching
- **Recharts** - Data visualization
- **Socket.io Client** - Real-time features

## Project Structure


## Quick Start

### Prerequisites

- Python 3.11+ and Node.js 20+
- PostgreSQL (optional - SQLite can be used for development)
- Docker (optional - for PostgreSQL via Docker)

### Quickest Start (SQLite - No Database Setup Needed!)

1. **Windows**: Double-click `start_clovio.bat`  
2. **PowerShell**: Run `.\start_clovio.ps1`  
3. **Linux/Mac**: Run `python backend/start_backend.py`  

This will automatically:  
- Use SQLite (no PostgreSQL needed!)  
- Generate secret key  
- Create database and tables  
- Start the server  

### Using Docker (PostgreSQL)

1. Clone the repository:
```bash
git clone <repository-url>
cd Clovio

cd backend
pip install -r requirements.txt
python main.py

cd frontend
npm install
npm run dev


