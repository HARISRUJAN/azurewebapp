# PowerShell script to create .env file
$envContent = @"
# Database
DATABASE_URL=sqlite:///./aigov.db

# JWT
SECRET_KEY=change-this-to-a-random-secret-key-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI - REQUIRED: Add your OpenAI API key here
OPENAI_API_KEY=

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=aigov_documents

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
"@

$envPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envPath)) {
    $envContent | Out-File -FilePath $envPath -Encoding utf8
    Write-Host "✅ Created .env file at: $envPath" -ForegroundColor Green
    Write-Host "⚠️  Please add your OPENAI_API_KEY to the .env file!" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  .env file already exists at: $envPath" -ForegroundColor Yellow
    Write-Host "   Please check and update it manually if needed." -ForegroundColor Yellow
}

