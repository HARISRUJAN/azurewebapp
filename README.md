# AI Governance Literacy Platform

A production-ready platform making AI regulation and risk frameworks understandable, trustworthy, and accessible to policy professionals, researchers, civil society, and the public.

## Overview

The AI Governance Literacy Platform provides an intelligent question-answering system powered by Retrieval-Augmented Generation (RAG) technology. It enables users to query comprehensive AI governance documents including the NIST AI Risk Management Framework and EU AI Act, receiving accurate, cited answers from authoritative sources.

## Architecture

### Tech Stack

**Backend:**
- **FastAPI** - High-performance Python web framework
- **SQLAlchemy** - ORM for database management
- **Qdrant** - Vector database for semantic search
- **spaCy** - Semantic chunking and entity extraction (paragraph-based)
- **Nomic Embeddings** - Local embedding generation (sentence-transformers)
- **Groq** - Fast LLM inference for answer generation
- **JWT** - Secure authentication

**Frontend:**
- **React + TypeScript** - Modern UI framework
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **React Query** - Data fetching and state management
- **React Router** - Client-side routing
- **Nginx** - Production web server

### System Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   Backend    │─────▶│   Qdrant    │
│   (React)   │      │   (FastAPI)  │      │  (Vector DB)│
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Database   │
                     │  (SQLite/    │
                     │  PostgreSQL) │
                     └──────────────┘
```

## Features

### Public Features
- **Intelligent Q&A** - Ask questions about AI governance frameworks
- **Source Citations** - Every answer includes references to source documents
- **Semantic Search** - Advanced vector-based document retrieval
- **Responsive Design** - Works seamlessly on desktop and mobile

### Admin Features
- **Document Management** - Ingest and manage governance documents
- **Origin Configuration** - Configure document sources
- **System Health Monitoring** - Monitor system status and performance
- **User Authentication** - Secure JWT-based admin access

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+ (recommended)
- OR **Python** 3.11+ and **Node.js** 18+ (for local development)
- **Qdrant** (local or cloud instance)

## Quick Start

### Local Development (Recommended for V1)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd aigov
   ```

2. **Configure environment:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API keys (see Environment Configuration below)
   ```

3. **Install dependencies:**
   ```bash
   # Backend
   python -m venv aigov_env
   source aigov_env/bin/activate  # Linux/Mac
   aigov_env\Scripts\activate     # Windows
   pip install -r requirements.txt
   
   # Install spaCy English model (required for semantic chunking)
   python -m spacy download en_core_web_md
   
   # Frontend
   cd ../frontend
   npm install
   ```

4. **Initialize database:**
   ```bash
   cd ../backend
   python scripts/init_db.py
   ```

5. **Start services:**
   ```bash
   # Terminal 1: Backend (from backend directory)
   python run_server.py
   
   # Terminal 2: Frontend (from frontend directory)
   npm run dev
   ```

6. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Admin Login: http://localhost:5173/admin/login
     - Default credentials: `admin` / `admin123` (change in production!)

7. **Seed initial documents (optional):**
   ```bash
   cd backend
   python scripts/seed_documents.py
   ```

## Quick Start with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sidd07181134/ArtigenAI.git
   cd ArtigenAI
   ```

2. **Configure environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys and configuration
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database:**
   ```bash
   docker-compose exec backend python scripts/init_db.py
   ```

5. **Seed initial documents:**
   ```bash
   docker-compose exec backend python scripts/seed_documents.py
   ```

6. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Qdrant Dashboard: http://localhost:6333/dashboard

## Environment Configuration

Create a `.env` file in the `backend/` directory based on `.env.example`. Required variables:

### Required Variables
- `SECRET_KEY` - JWT signing key (generate with: `openssl rand -hex 32`)
- `GROQ_API_KEY` - Groq API key for answer generation
- `QDRANT_URL` - Qdrant vector database URL
- `QDRANT_API_KEY` - Qdrant API key (if using Qdrant Cloud)

### Optional Variables
- `DATABASE_URL` - Database connection string (default: SQLite)
- `OPENAI_API_KEY` - OpenAI API key (optional fallback)
- `CORS_ORIGINS` - Comma-separated allowed origins

See `backend/.env.example` for complete configuration options.

## API Documentation

### Public Endpoints

**Query the RAG System:**
```http
POST /api/search/query
Content-Type: application/json

{
  "question": "What is the EU AI Act?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "The EU AI Act is...",
  "citations": [
    {
      "content": "Document chunk...",
      "document_title": "EU AI Act",
      "document_source": "European Commission",
      "document_url": "https://...",
      "chunk_index": 0
    }
  ]
}
```

### Admin Endpoints (Require Authentication)

- `POST /api/auth/login` - Admin login
- `GET /api/auth/me` - Get current user
- `POST /api/content/ingest` - Ingest documents
- `GET /api/admin/origins` - List scraping origins
- `POST /api/admin/origins` - Create origin
- `PUT /api/admin/origins/{id}` - Update origin
- `DELETE /api/admin/origins/{id}` - Delete origin
- `GET /api/admin/health` - System health status

Full API documentation available at `/docs` when the backend is running.

## Development Setup

### Backend

1. **Create virtual environment:**
   ```bash
   python -m venv aigov_env
   source aigov_env/bin/activate  # Linux/Mac
   aigov_env\Scripts\activate     # Windows
   ```

2. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

5. **Seed documents:**
   ```bash
   python scripts/seed_documents.py
   ```

6. **Run development server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

## Production Deployment

For production deployment supporting 10,000+ users, see [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Scaling considerations
- Database migration to PostgreSQL
- Load balancing setup
- Monitoring and logging
- Security best practices
- Backup procedures

## Security

- All API keys and secrets are managed via environment variables
- JWT-based authentication for admin endpoints
- CORS protection configured
- Input validation and sanitization
- Non-root Docker containers
- Security headers in production

**Important:** Change default admin credentials before deploying to production!

## Default Credentials

**Admin Login (Development Only):**
- Username: `admin`
- Password: `admin123`

⚠️ **These must be changed in production!**

## Project Structure

```
aigov/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── services/     # Business logic
│   │   ├── models/       # Database models and schemas
│   │   ├── core/         # Configuration and security
│   │   └── main.py       # FastAPI app entry point
│   ├── scripts/          # Utility scripts
│   ├── data/            # PDF documents for ingestion
│   ├── Dockerfile       # Backend container definition
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API client
│   │   └── hooks/       # React hooks
│   ├── Dockerfile       # Frontend container definition
│   └── package.json     # Node dependencies
├── docker-compose.yml   # Container orchestration
└── README.md           # This file
```

## Contributing

This is a non-profit platform for AI governance literacy. Contributions are welcome.

## License

This project is developed for non-profit use in AI governance literacy.

## Support

For deployment issues, see [DEPLOYMENT.md](DEPLOYMENT.md). For API documentation, visit `/docs` when the backend is running.
