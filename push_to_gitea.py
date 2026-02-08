#!/usr/bin/env python3
"""
Push the current backend project to Gitea using the API.
Based on the Gitea Agent Interaction Guide.
"""
import os
import base64
import requests
import json
from pathlib import Path

# Gitea Configuration
GITEA_HOST = "http://192.168.178.84:3000"
GITEA_OWNER = "CodingLawyerX"
GITEA_TOKEN = "18762817246cfed0e79ca7068288bd4042ea80d3"
USER_NAME = "Steffen Gross"
USER_EMAIL = "steffen.gross@simpliant.eu"

# Repository name (extract from directory or define)
REPO_NAME = "transcription-platform-backend"

# Headers for API requests
headers = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json"
}

def get_repo_info(owner, repo_name):
    """Get repository information."""
    url = f"{GITEA_HOST}/api/v1/repos/{owner}/{repo_name}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        raise Exception(f"Failed to get repo info: {response.status_code} {response.text}")

def create_repository(repo_name, description="", private=True):
    """Create a new repository."""
    url = f"{GITEA_HOST}/api/v1/user/repos"
    data = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False,  # We'll push files ourselves
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in (201, 200):
        return response.json()
    else:
        raise Exception(f"Failed to create repo: {response.status_code} {response.text}")

def get_file_sha(owner, repo_name, file_path, branch="main"):
    """Get SHA of existing file."""
    url = f"{GITEA_HOST}/api/v1/repos/{owner}/{repo_name}/contents/{file_path}"
    params = {"ref": branch}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('sha')
    return None

def create_or_update_file(owner, repo_name, file_path, content, commit_message, branch="main"):
    """Create or update a file via API."""
    url = f"{GITEA_HOST}/api/v1/repos/{owner}/{repo_name}/contents/{file_path}"
    
    # Check if file exists to get SHA for update
    sha = get_file_sha(owner, repo_name, file_path, branch)
    
    # Prepare data
    data = {
        "message": commit_message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": branch
    }
    if sha:
        data["sha"] = sha
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in (201, 200):
        return response.json()
    else:
        raise Exception(f"Failed to create/update file {file_path}: {response.status_code} {response.text}")

def walk_directory(root_dir):
    """Yield all files in directory recursively."""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            yield full_path

def should_ignore(path):
    """Ignore certain files/directories."""
    ignore_patterns = [
        '.git', '__pycache__', '.pytest_cache', '.venv', 'venv',
        'node_modules', '.idea', '.vscode', '*.pyc', '.env', '.DS_Store',
        '*.log', '*.sqlite3', '*.db', '*.pid', '*.so', '*.o', '*.egg-info',
        'staticfiles', 'media', 'uploads', 'dist', 'build', '*.egg',
        'docker-compose.override.yml', 'docker-compose.prod.yml',
        '.dockerignore', '.gitignore', '.gitattributes',
    ]
    path_str = str(path)
    for pattern in ignore_patterns:
        if pattern in path_str:
            return True
    return False

def main():
    print("=== Pushing transcription-platform backend to Gitea ===")
    
    # Determine project root (current directory)
    project_root = Path.cwd()
    print(f"Project root: {project_root}")
    
    # Check if repository exists
    repo_info = get_repo_info(GITEA_OWNER, REPO_NAME)
    if repo_info is None:
        print(f"Repository '{REPO_NAME}' does not exist. Creating...")
        repo_info = create_repository(
            REPO_NAME,
            description="Django backend for transcription platform with Celery & Voxtral integration",
            private=True
        )
        print(f"Repository created: {repo_info['html_url']}")
    else:
        print(f"Repository already exists: {repo_info['html_url']}")
    
    # Collect files to upload
    files = []
    for file_path in walk_directory(project_root):
        if should_ignore(file_path):
            continue
        rel_path = os.path.relpath(file_path, project_root)
        # Skip the script itself
        if rel_path == 'push_to_gitea.py':
            continue
        files.append((rel_path, file_path))
    
    print(f"Found {len(files)} files to upload.")
    
    # Upload each file
    for i, (rel_path, abs_path) in enumerate(files):
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Binary file? Skip for now.
            print(f"Skipping binary file: {rel_path}")
            continue
        
        print(f"[{i+1}/{len(files)}] Uploading {rel_path}...")
        try:
            result = create_or_update_file(
                GITEA_OWNER,
                REPO_NAME,
                rel_path,
                content,
                f"Add {rel_path} via API",
                branch="main"
            )
        except Exception as e:
            print(f"  Error: {e}")
    
    print("=== Upload completed ===")
    print(f"Repository URL: {GITEA_HOST}/{GITEA_OWNER}/{REPO_NAME}")

if __name__ == "__main__":
    main()