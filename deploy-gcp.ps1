# Trinity Cloud Deployment Script for Google Cloud Run
# Prerequisites: Install Google Cloud SDK and authenticate

$PROJECT_ID = Read-Host "Enter your Google Cloud Project ID"
$REGION = "europe-west1"
$SERVICE_NAME = "trinity-ui"

Write-Host "🚀 Deploying Trinity UI to Google Cloud Run..." -ForegroundColor Cyan

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud --version 2>$null
    Write-Host "✅ Google Cloud SDK found" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK not installed" -ForegroundColor Red
    Write-Host "Install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Set project
Write-Host "`n📝 Setting project: $PROJECT_ID" -ForegroundColor Cyan
gcloud config set project $PROJECT_ID

# Enable required APIs
Write-Host "`n🔧 Enabling required APIs..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Build container
Write-Host "`n🏗️ Building container image..." -ForegroundColor Cyan
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

# Deploy to Cloud Run
Write-Host "`n🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8000 `
    --memory 512Mi `
    --cpu 1 `
    --max-instances 3 `
    --set-env-vars "TRINITY_ENGINE_URL=http://localhost:9000/api/chat"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
    Write-Host "`n🌐 Your Trinity UI is now live at:" -ForegroundColor Cyan
    $SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)"
    Write-Host $SERVICE_URL -ForegroundColor Yellow
    Write-Host "`n📱 Test microphone on your phone by opening this URL" -ForegroundColor Green
} else {
    Write-Host "`n❌ Deployment failed" -ForegroundColor Red
    exit 1
}
