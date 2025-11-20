# Quick Setup Instructions

## ✅ What's Already Done
- ✅ Virtual environment created (`aigov_env`)
- ✅ Backend dependencies installed
- ✅ Frontend dependencies installed
- ✅ Database initialized
- ✅ `.env` file created (needs your API keys)

## 🔧 What You Need to Add

### 1. Add Your API Keys

Edit `backend/.env` and add your API keys:

**Groq API Key (Required for answer generation):**
```env
GROQ_API_KEY=gsk-your-actual-groq-api-key-here
```

Get your Groq API key from: https://console.groq.com/keys

**OpenAI API Key (Required for embeddings):**
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

**Note:** The platform uses:
- **Groq** for answer generation (primary LLM)
- **OpenAI** for embeddings (required - Groq doesn't provide embedding models)

### 2. Configure Qdrant Vector Database

**Using Qdrant Cloud (Recommended)**
1. Get your Qdrant Cloud URL from your cluster dashboard
2. Update `backend/.env` with your Qdrant Cloud URL:
   ```env
   QDRANT_URL=https://your-cluster-id.qdrant.io
   ```
   Or if you have an API key:
   ```env
   QDRANT_URL=https://your-cluster-id.qdrant.io
   QDRANT_API_KEY=your-api-key-here
   ```

**Alternative: Local Qdrant (if not using cloud)**
- **Option A: Using Docker**
  ```bash
  docker run -p 6333:6333 qdrant/qdrant
  ```
- **Option B: Download Qdrant**
  1. Download from: https://qdrant.tech/documentation/guides/installation/
  2. Extract and run: `qdrant.exe` (Windows) or `./qdrant` (Linux/Mac)
  3. It will start on port 6333 by default

### 3. Seed Initial Documents

After Qdrant is running, seed the initial documents:

```bash
cd backend
..\aigov_env\Scripts\python.exe scripts\seed_documents.py
```

This will add:
- NIST AI Risk Management Framework overview
- EU AI Act summary

## 🚀 Running the Application

### Backend (should already be running)
```bash
cd backend
..\aigov_env\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Frontend (should already be running)
```bash
cd frontend
npm run dev
```

## 🔐 Default Admin Credentials

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Change these in production!**

## 📍 Access Points

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Qdrant Dashboard:** http://localhost:6333/dashboard (if running locally)

## ✅ Verification Checklist

- [ ] Groq API key added to `backend/.env`
- [ ] OpenAI API key added to `backend/.env` (for embeddings)
- [ ] Qdrant configured (Cloud URL and API key in `.env`)
- [ ] Seed documents script run successfully
- [ ] Backend server running on port 8000
- [ ] Frontend server running on port 5173
- [ ] Can access frontend at http://localhost:5173
- [ ] Can login to admin at http://localhost:5173/admin/login
- [ ] Can ask questions and get answers (tests Groq integration)

## 🐛 Troubleshooting

### Qdrant Connection Error
- Make sure Qdrant is running: `Test-NetConnection localhost -Port 6333`
- Check `QDRANT_URL` in `.env` matches your Qdrant instance

### Groq API Errors
- Verify your Groq API key is correct in `backend/.env`
- Check you have credits/quota on your Groq account
- Make sure the key starts with `gsk_`
- The platform uses Groq for answer generation

### OpenAI API Errors
- Verify your OpenAI API key is correct in `backend/.env`
- Check you have credits/quota on your OpenAI account
- Make sure the key starts with `sk-`
- OpenAI is required for embeddings (Groq doesn't provide embedding models)

### Database Errors
- Delete `backend/aigov.db` and re-run `scripts/init_db.py`
- Make sure SQLite is working (should be included with Python)

### Port Already in Use
- Backend: Change port in `uvicorn` command or kill process on port 8000
- Frontend: Change port in `vite.config.ts` or kill process on port 5173
- Qdrant: Change port in Docker command or Qdrant config

