#!/bin/bash
set -e

# Configuration
GITEA_HOST="http://192.168.178.84:3000"
GITEA_OWNER="CodingLawyerX"
GITEA_TOKEN="18762817246cfed0e79ca7068288bd4042ea80d3"
REPO_NAME="transcription-platform-backend"
REPO_DESC="Django backend for transcription platform with Celery & Voxtral integration"

# Construct remote URL with token
REMOTE_URL="http://$GITEA_OWNER:$GITEA_TOKEN@192.168.178.84:3000/$GITEA_OWNER/$REPO_NAME.git"

# Check if repository exists via API
echo "Checking if repository $REPO_NAME exists..."
response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $GITEA_TOKEN" \
    "$GITEA_HOST/api/v1/repos/$GITEA_OWNER/$REPO_NAME")

if [ "$response" = "404" ]; then
    echo "Repository does not exist. Creating..."
    curl -X POST -H "Authorization: token $GITEA_TOKEN" -H "Content-Type: application/json" \
        -d "{\"name\":\"$REPO_NAME\", \"description\":\"$REPO_DESC\", \"private\":true, \"auto_init\":false}" \
        "$GITEA_HOST/api/v1/user/repos"
    echo "Repository created."
elif [ "$response" = "200" ]; then
    echo "Repository already exists."
else
    echo "Unexpected response: $response"
    exit 1
fi

# Initialize git repository if not already
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git config user.name "Steffen Gross"
    git config user.email "steffen.gross@simpliant.eu"
fi

# Add remote (replace if exists)
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"

# Add all files
git add .

# Commit
git commit -m "Initial commit: Transcription Platform Backend with Celery & Voxtral integration" || echo "No changes to commit"

# Push with token authentication (force push to overwrite remote)
echo "Pushing to Gitea (force push)..."
git push -u origin main --force 2>/dev/null || git push -u origin master --force 2>/dev/null || {
    # If branch doesn't exist, create it
    git branch -M main
    git push -u origin main --force
}

echo "Push completed successfully!"
echo "Repository URL: $GITEA_HOST/$GITEA_OWNER/$REPO_NAME"