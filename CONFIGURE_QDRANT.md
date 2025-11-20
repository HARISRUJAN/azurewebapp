# Configure Qdrant Cloud

## Quick Setup

When you provide your Qdrant Cloud link, I'll help you configure it. Here's what you need:

### Information Needed:
1. **Qdrant Cloud URL** - Usually looks like: `https://xxxxx-xxxxx.qdrant.io`
2. **API Key** (if required) - Found in your Qdrant Cloud dashboard

### Steps:

1. **Edit `backend/.env`** and update:
   ```env
   QDRANT_URL=https://your-cluster-id.qdrant.io
   QDRANT_API_KEY=your-api-key-here  # If your cluster requires it
   ```

2. **Test the connection** by running:
   ```bash
   cd backend
   ..\aigov_env\Scripts\python.exe scripts\seed_documents.py
   ```

3. **If successful**, you'll see:
   ```
   ✓ NIST AI RMF ingested
   ✓ EU AI Act ingested
   Seed documents created successfully!
   ```

## What to Provide

Just share:
- Your Qdrant Cloud URL (e.g., `https://abc123-def456.qdrant.io`)
- Your API key (if required by your cluster)

I'll update the configuration for you!

