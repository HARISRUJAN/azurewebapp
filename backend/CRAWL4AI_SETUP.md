# Crawl4AI Setup Instructions

## Initial Setup

Crawl4AI requires a one-time setup command to be run after installation:

```bash
crawl4ai-setup
```

This command:
- Downloads required browser dependencies
- Sets up the crawling environment
- Configures necessary components

**Important:** This must be run once before using the crawling functionality.

## Running the Setup

### Option 1: Manual Setup (Recommended for Development)

```bash
# Activate your virtual environment
source aigov_env/bin/activate  # Linux/Mac
# OR
aigov_env\Scripts\activate     # Windows

# Run the setup command
crawl4ai-setup
```

### Option 2: Docker Setup

If using Docker, add this to your Dockerfile or run it in the container:

```dockerfile
# In Dockerfile, after installing requirements
RUN crawl4ai-setup
```

Or run it manually in a running container:

```bash
docker-compose exec backend crawl4ai-setup
```

## Verification

After running `crawl4ai-setup`, you can verify the installation by testing the crawl endpoint:

```bash
curl "http://localhost:8000/api/crawl?url=https://crawl4ai.com"
```

## Troubleshooting

If you encounter errors:
1. Ensure `crawl4ai-setup` has been run
2. Check that all dependencies are installed: `pip install -r requirements.txt`
3. Verify network connectivity for the URLs you're trying to crawl
4. Check application logs for detailed error messages

## Notes

- The setup only needs to be run once per environment
- It may take a few minutes to complete (downloads browser dependencies)
- No API keys are required for basic crawling functionality
- PDF support is built into Crawl4AI and works automatically

