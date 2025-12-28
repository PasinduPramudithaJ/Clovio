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

```
Clovio/
├── backend/
│   ├── ai/                 # AI services (skill extraction, task assignment)
│   ├── routers/            # API route handlers
│   ├── models.py          # Database models
│   ├── schemas.py         # Pydantic schemas
│   ├── auth.py            # Authentication utilities
│   ├── database.py        # Database configuration
│   ├── utils.py           # Utility functions (auto secret key generation)
│   ├── generate_secret_key.py  # Manual secret key generator
│   ├── init_db.py         # Database initialization script
│   └── main.py            # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # Utilities and API client
│   │   └── store/         # State management
│   └── package.json
├── docker-compose.yml      # Docker orchestration
└── README.md
```

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
```

2. Start PostgreSQL:
```bash
# Windows: Double-click start_postgres.bat or run:
.\start_postgres.ps1
```

3. Start backend:
```bash
cd backend
python main.py
```

4. Access the application:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL database:

**Option A: Quick Start Scripts (Recommended)**
- **Windows**: Double-click `start_postgres.bat` or run `.\start_postgres.ps1` in PowerShell
- **Linux/Mac**: Run `bash start_postgres.sh`

**Option B: Use Docker Manually**
```bash
docker run -d --name clovio_db -e POSTGRES_USER=clovio_user -e POSTGRES_PASSWORD=clovio_pass -e POSTGRES_DB=clovio_db -p 5432:5432 postgres:15-alpine
```

**Option C: Start Local PostgreSQL Service**
- **Windows**: Start PostgreSQL service from Services (services.msc) or use pgAdmin
- **Linux**: `sudo systemctl start postgresql`
- **Mac**: `brew services start postgresql`

**Note:** The database will be created automatically when you start the server. Just ensure PostgreSQL is running first.

5. Create `.env` file (optional - secret key will be auto-generated):
```env
DATABASE_URL=postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db
SECRET_KEY=your-secret-key-here  # Optional: Will be auto-generated if not set
OPENAI_API_KEY=your-openai-api-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Note:** The `SECRET_KEY` will be automatically generated and saved to your `.env` file on first run if you don't set it. You can also manually generate one by running:
```bash
cd backend
python generate_secret_key.py
```

6. Initialize database (optional - database and tables are created automatically on first run):
```bash
# The database will be created automatically, but you can also run:
python init_db.py
```

7. Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file (optional):
```env
VITE_API_URL=http://localhost:8000
```

4. Start development server:
```bash
npm run dev
```

5. Open http://localhost:3000 in your browser

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Key Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login-json` - Login with JSON
- `GET /api/auth/me` - Get current user

### Projects
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `GET /api/projects/{id}` - Get project details
- `POST /api/projects/{id}/breakdown` - AI breakdown project into tasks

### Tasks
- `GET /api/tasks/` - List tasks
- `POST /api/tasks/` - Create task
- `PATCH /api/tasks/{id}` - Update task
- `POST /api/tasks/assign-ai` - AI assign tasks

### Documents
- `GET /api/documents/?project_id={id}` - List documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents/{id}/download` - Download document

### Chat
- `GET /api/chat/project/{id}` - Get messages
- `POST /api/chat/` - Send message

### Analytics
- `GET /api/analytics/dashboard` - Professor dashboard stats
- `GET /api/analytics/project/{id}` - Project analytics
- `GET /api/analytics/user/{id}` - User analytics

## Environment Variables

### Backend
- `USE_SQLITE` - Set to "true" to use SQLite instead of PostgreSQL (default: false)
- `DATABASE_URL` - Database connection string (optional - defaults based on USE_SQLITE)
  - SQLite: `sqlite:///./clovio.db`
  - PostgreSQL: `postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db`
- `SECRET_KEY` - JWT secret key (optional - auto-generated on first run if not set)
- `OPENAI_API_KEY` - OpenAI API key for AI features (optional - AI features will use fallback if not set)
- `CORS_ORIGINS` - Allowed CORS origins (optional - defaults to localhost:3000 and localhost:5173)

### Automatic Setup Features

**Automatic Secret Key Generation:**
- If `SECRET_KEY` is missing from `.env`, a new one is generated automatically
- The generated key is automatically saved to your `.env` file
- No manual configuration needed - just start the server!

**Automatic Database Setup:**
- **SQLite Mode**: No setup needed! Just set `USE_SQLITE=true` in `.env`
- **PostgreSQL Mode**: Database is created automatically if it doesn't exist
- Database tables are created automatically on first run
- No manual database setup required!

**Manual Setup (Optional):**
If you prefer to set things up manually:
```bash
# Generate secret key
cd backend
python generate_secret_key.py

# Initialize database
python init_db.py

# Or use setup scripts:
# Windows: .\backend\setup_database.ps1
# Linux/Mac: bash backend/setup_database.sh
```

### Frontend
- `VITE_API_URL` - Backend API URL

## Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Code Formatting
```bash
# Backend
black .
isort .

# Frontend
npm run lint
```

## Production Deployment

1. Set production environment variables
2. Build frontend: `npm run build`
3. Use production WSGI server (e.g., Gunicorn with Uvicorn workers)
4. Serve frontend with Nginx or similar
5. Set up SSL certificates
6. Configure database backups

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
#   C l o v i o  
 