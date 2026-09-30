import os
import sys
import subprocess
import urllib.request
import json

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        env = dict(os.environ, GCM_INTERACTIVE="never")
        p = subprocess.Popen(
            ['git', 'credential', 'fill'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        out, _ = p.communicate(input='protocol=https\nhost=github.com\n\n', timeout=3)
        creds = dict(line.split('=', 1) for line in out.strip().splitlines() if '=' in line)
        return creds.get('password')
    except Exception as e:
        print(f"[WARN] Failed to retrieve git credential: {e}")
        return None

def get_current_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except Exception as e:
        print(f"[WARN] Failed to get HEAD commit SHA: {e}")
        return None

def report_status(state, description, context="continuous-integration/jenkins/branch"):
    token = get_github_token()
    commit_sha = get_current_commit()

    if not token or not commit_sha:
        print("[INFO] GitHub token or commit SHA not available; skipping status report.")
        return

    repo = "reddykajakarthikeya-sketch/online_voting_system"
    url = f"https://api.github.com/repos/{repo}/statuses/{commit_sha}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Jenkins-CI"
    }
    payload = {
        "state": state,
        "description": description,
        "context": context
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            print(f"[INFO] GitHub status reported: {context} -> {state}")
    except Exception as e:
        print(f"[WARN] Failed to post status to GitHub: {e}")

if __name__ == "__main__":
    state = sys.argv[1] if len(sys.argv) > 1 else "success"
    desc = sys.argv[2] if len(sys.argv) > 2 else "Jenkins CI completed"
    report_status(state, desc)
