"""Fail any case that holds private data.

Usage: python3 scripts/check_masking.py [case files...]
With no files, checks cases that are new or changed against origin/main.
Prints MASK_FAILED <case ID> <reason> per failure and exits 1, or MASK_OK.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = [
    "buddyboss.com", "wordpress.org", "developer.apple.com", "developer.android.com",
    "support.google.com", "github.com", "cloudflare.com",
    # reserved placeholder domains, never a real site
    "example.com", "example.org", "example.net",
]
TLDS = (
    "com|net|org|io|co|app|dev|info|biz|me|us|uk|ca|au|de|fr|nl|es|it|in|edu|gov|online|site|"
    "store|shop|tech|xyz|club|live|pro|academy|community|school|life|world|digital|agency|cloud|ai"
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)([^\s/'\"<>)\]]+)")
DOMAIN_RE = re.compile(r"(?i)(?<![\w@/.-])((?:[a-z0-9-]+\.)+(?:%s))(?![\w-])" % TLDS)
IP_RE = re.compile(r"(?<![\d.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])")
CRED_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|user\s*name|username|login|s?ftp|ssh|api[\s_-]?key|secret|token|license[\s_-]?key)"
    r"\s*[:=]\s*[\"']?[^\s\"']{3,}"
    r"|\b(password|passwd|pwd)\s+is\s+[\"']?[^\s\"']{3,}"
)
KEY_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{24,}(?![A-Za-z0-9])")


def host_allowed(host):
    host = host.lower().split(":")[0].split("@")[-1].rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def check_text(text):
    """Return the first reason found, or None."""
    for line in text.split("\n"):
        if EMAIL_RE.search(line):
            return "email"
        for m in URL_RE.finditer(line):
            if not host_allowed(m.group(1)):
                return "url " + m.group(1).lower().split("/")[0][:40]
        for m in DOMAIN_RE.finditer(line):
            if not host_allowed(m.group(1)):
                return "domain " + m.group(1).lower()[:40]
        for m in IP_RE.finditer(line):
            if all(int(p) <= 255 for p in m.groups()):
                return "ip address"
        m = CRED_RE.search(line)
        if m:
            return "credential line " + (m.group(1) or m.group(2)).lower()
        for m in KEY_RE.finditer(line):
            s = m.group(0)
            if re.search(r"\d", s) and re.search(r"[A-Za-z]", s) or len(s) >= 32:
                return "key-like string"
    return None


def changed_cases():
    def git(*args):
        r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True)
        return r.stdout.split("\n") if r.returncode == 0 else []

    files = set()
    for line in git("status", "--porcelain", "--untracked-files=all", "--", "cases"):
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        if path.endswith(".md"):
            files.add(path)
    for path in git("diff", "--name-only", "--diff-filter=AM", "origin/main", "HEAD", "--", "cases"):
        if path.endswith(".md"):
            files.add(path.strip())
    return sorted(os.path.join(ROOT, f) for f in files)


def case_id(path):
    p = os.path.abspath(path).replace(os.sep, "/")
    parts = p.split("/")
    return "%s/%s" % (parts[-2], parts[-1][:-3]) if p.endswith(".md") else p


def main():
    paths = sys.argv[1:] or changed_cases()
    failed = False
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            reason = check_text(f.read())
        if reason:
            failed = True
            print("MASK_FAILED %s %s" % (case_id(path), reason))
    if failed:
        sys.exit(1)
    print("MASK_OK")


if __name__ == "__main__":
    main()
