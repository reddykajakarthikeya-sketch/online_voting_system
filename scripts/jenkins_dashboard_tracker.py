import os
import sys
import subprocess
import urllib.request
import json
from datetime import datetime

def get_git_credential_token():
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
    except Exception:
        return None

def get_git_info():
    info = {}
    try:
        info['commit_hash'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        info['short_hash'] = info['commit_hash'][:7]
        info['author_name'] = subprocess.check_output(['git', 'log', '-1', '--format=%an'], text=True).strip()
        info['author_email'] = subprocess.check_output(['git', 'log', '-1', '--format=%ae'], text=True).strip()
        info['commit_msg'] = subprocess.check_output(['git', 'log', '-1', '--format=%s'], text=True).strip()
        info['commit_date'] = subprocess.check_output(['git', 'log', '-1', '--format=%cd', '--date=iso'], text=True).strip()
        info['branch'] = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except Exception as e:
        info['error'] = str(e)
    return info

def get_team_contributions():
    contributions = {}
    try:
        # Get recent 50 commits (non-merge commits)
        log_out = subprocess.check_output(
            ['git', 'log', '--no-merges', '-n', '50', '--format=%an|%h|%s|%cd', '--date=short'],
            text=True
        ).strip().splitlines()
        
        for line in log_out:
            parts = line.split('|', 3)
            if len(parts) == 4:
                author, chash, msg, cdate = parts
                if author not in contributions:
                    contributions[author] = {'count': 0, 'recent_commits': []}
                contributions[author]['count'] += 1
                if len(contributions[author]['recent_commits']) < 3:
                    contributions[author]['recent_commits'].append({'hash': chash, 'msg': msg, 'date': cdate})
    except Exception as e:
        print(f"[WARN] Failed to parse git log for contributions: {e}")
    return contributions

def fetch_github_pull_requests(token):
    repo = "reddykajakarthikeya-sketch/online_voting_system"
    url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=10"
    headers = {"User-Agent": "Jenkins-Dashboard"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github+json"

    prs = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for item in data:
                # fetch reviews for PR
                reviews_url = item.get('_links', {}).get('review_comments', {}).get('href', '')
                pr_info = {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "author": item.get("user", {}).get("login"),
                    "state": item.get("state"),
                    "is_merged": bool(item.get("merged_at")),
                    "source_branch": item.get("head", {}).get("ref"),
                    "target_branch": item.get("base", {}).get("ref"),
                    "html_url": item.get("html_url"),
                    "created_at": item.get("created_at"),
                    "requested_reviewers": [r.get("login") for r in item.get("requested_reviewers", [])]
                }
                prs.append(pr_info)
    except Exception as e:
        print(f"[WARN] Failed to fetch PRs from GitHub: {e}")
    return prs

def generate_dashboard():
    token = get_git_credential_token()
    git_info = get_git_info()
    contributions = get_team_contributions()
    prs = fetch_github_pull_requests(token)

    # Read test summary
    test_summary = {"total": 0, "passed": 0, "failed": 0, "duration_seconds": 0}
    test_file = os.path.join("test-reports", "summary.json")
    if os.path.exists(test_file):
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                test_summary = json.load(f)
        except Exception:
            pass

    # Check deployment target
    deploy_dir = r"C:\deploy\online_voting_system"
    deploy_status = "Available" if os.path.exists(deploy_dir) else "Pending Initial Setup"
    is_main = git_info.get("branch") == "main"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Render HTML Dashboard Snippet
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 950px; background: #ffffff; border: 1px solid #e1e4e8; border-radius: 12px; padding: 20px; color: #24292e; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0366d6; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #0366d6; font-size: 1.4rem;">🗳️ Online Voting System &mdash; CI/CD Workflow Dashboard</h2>
            <span style="font-size: 0.85rem; color: #586069; background: #f1f8ff; padding: 4px 10px; border-radius: 20px; border: 1px solid #c8e1ff;">Updated: {now_str}</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;">
            <div style="background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.8rem; color: #586069; font-weight: bold; text-transform: uppercase;">Build Target</div>
                <div style="font-size: 1.1rem; font-weight: bold; color: #24292e; margin-top: 4px;">Branch: <span style="color: #0366d6;">{git_info.get('branch', 'unknown')}</span></div>
                <div style="font-size: 0.85rem; color: #586069;">Commit: <code>{git_info.get('short_hash', 'N/A')}</code></div>
            </div>

            <div style="background: {'#dcffe4' if test_summary.get('failed', 0) == 0 else '#ffdce0'}; border: 1px solid {'#34d058' if test_summary.get('failed', 0) == 0 else '#ea4a5a'}; border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.8rem; color: #586069; font-weight: bold; text-transform: uppercase;">Automated Tests</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: {'#22863a' if test_summary.get('failed', 0) == 0 else '#cb2431'}; margin-top: 4px;">
                    {test_summary.get('passed', 0)} / {test_summary.get('total', 0)} Passed
                </div>
                <div style="font-size: 0.85rem; color: #586069;">Duration: {test_summary.get('duration_seconds', 0)}s</div>
            </div>

            <div style="background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.8rem; color: #586069; font-weight: bold; text-transform: uppercase;">Deployment (Staging)</div>
                <div style="font-size: 1rem; font-weight: bold; color: {'#22863a' if is_main else '#b08800'}; margin-top: 4px;">
                    {'Active (C:\\deploy)' if is_main else 'Skipped (Non-Main Branch)'}
                </div>
                <div style="font-size: 0.8rem; color: #586069;">Directory: <code>{deploy_dir}</code></div>
            </div>
        </div>

        <div style="margin-bottom: 25px;">
            <h3 style="margin-top: 0; font-size: 1.05rem; border-bottom: 1px solid #eaecef; padding-bottom: 6px;">👥 Team Member Contributions (Non-Merge Feature Commits)</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                <thead>
                    <tr style="background: #f6f8fa; border-bottom: 2px solid #e1e4e8; text-align: left;">
                        <th style="padding: 8px 12px;">Contributor</th>
                        <th style="padding: 8px 12px;">Feature Commits</th>
                        <th style="padding: 8px 12px;">Latest Contribution</th>
                    </tr>
                </thead>
                <tbody>
    """

    for author, cdata in contributions.items():
        recent_msg = cdata['recent_commits'][0]['msg'] if cdata['recent_commits'] else "N/A"
        recent_hash = cdata['recent_commits'][0]['hash'] if cdata['recent_commits'] else ""
        html += f"""
                    <tr style="border-bottom: 1px solid #eaecef;">
                        <td style="padding: 8px 12px; font-weight: bold; color: #0366d6;">👤 {author}</td>
                        <td style="padding: 8px 12px;"><span style="background: #24292e; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">{cdata['count']}</span></td>
                        <td style="padding: 8px 12px; color: #586069;"><code>{recent_hash}</code> {recent_msg}</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>

        <div>
            <h3 style="margin-top: 0; font-size: 1.05rem; border-bottom: 1px solid #eaecef; padding-bottom: 6px;">🔀 Pull Request Lifecycle & Review Tracking</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                <thead>
                    <tr style="background: #f6f8fa; border-bottom: 2px solid #e1e4e8; text-align: left;">
                        <th style="padding: 8px 12px;">PR #</th>
                        <th style="padding: 8px 12px;">Title</th>
                        <th style="padding: 8px 12px;">Author</th>
                        <th style="padding: 8px 12px;">Branches</th>
                        <th style="padding: 8px 12px;">Reviewers</th>
                        <th style="padding: 8px 12px;">Status</th>
                    </tr>
                </thead>
                <tbody>
    """

    for pr in prs:
        status_badge = ""
        if pr['is_merged']:
            status_badge = '<span style="background: #6f42c1; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold;">PURPLE / MERGED</span>'
        elif pr['state'] == 'open':
            status_badge = '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold;">GREEN / OPEN</span>'
        else:
            status_badge = '<span style="background: #cb2431; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold;">CLOSED</span>'

        revs = ", ".join(pr['requested_reviewers']) if pr['requested_reviewers'] else "None assigned"

        html += f"""
                    <tr style="border-bottom: 1px solid #eaecef;">
                        <td style="padding: 8px 12px; font-weight: bold;"><a href="{pr['html_url']}" target="_blank" style="color: #0366d6; text-decoration: none;">#{pr['number']}</a></td>
                        <td style="padding: 8px 12px;">{pr['title']}</td>
                        <td style="padding: 8px 12px; color: #586069;">@{pr['author']}</td>
                        <td style="padding: 8px 12px; font-size: 0.8rem; font-family: monospace;">{pr['source_branch']} &rarr; {pr['target_branch']}</td>
                        <td style="padding: 8px 12px; font-size: 0.85rem; color: #586069;">{revs}</td>
                        <td style="padding: 8px 12px;">{status_badge}</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>
    </div>
    """

    # Save to file
    with open("jenkins_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Save compact build description
    desc = f"Branch: {git_info.get('branch')} | Commit: {git_info.get('short_hash')} by {git_info.get('author_name')} | Tests: {test_summary.get('passed', 0)}/{test_summary.get('total', 0)} Passed"
    with open("build_description.txt", "w", encoding="utf-8") as f:
        f.write(desc)

    print("[INFO] Jenkins workflow dashboard generated successfully.")

if __name__ == '__main__':
    generate_dashboard()
