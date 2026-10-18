
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FOLDER = Path(r"C:\ApplicationMonitor")
LOG_FILE = FOLDER / "application_report.txt"

APPLICATIONS = [
    {
        "name": "Spotify",
        "website": "https://open.spotify.com",
        "status": "https://spotify.statuspage.io/api/v2/status.json",
        "incidents": "https://spotify.statuspage.io/api/v2/incidents.json"
    },
    {
        "name": "GitHub",
        "website": "https://github.com",
        "status": "https://www.githubstatus.com/api/v2/status.json",
        "incidents": "https://www.githubstatus.com/api/v2/incidents.json"
    },
    {
        "name": "Discord",
        "website": "https://discord.com",
        "status": "https://discordstatus.com/api/v2/status.json",
        "incidents": "https://discordstatus.com/api/v2/incidents.json"
    },
    {
        "name": "Cloudflare",
        "website": "https://www.cloudflare.com",
        "status": "https://www.cloudflarestatus.com/api/v2/status.json",
        "incidents": "https://www.cloudflarestatus.com/api/v2/incidents.json"
    }
]


def get_json(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "CollegeApplicationMonitor/1.0"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def website_status(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "CollegeApplicationMonitor/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return "ONLINE" if response.status < 400 else "ERROR"
    except Exception:
        return "UNREACHABLE"


def service_status(url):
    try:
        data = get_json(url)
        status = data.get("status", {})
        return status.get("description", "Status unknown")
    except Exception:
        return "Status unavailable"


def recent_incidents(url):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    try:
        data = get_json(url)
        found = []

        for incident in data.get("incidents", []):
            created = incident.get("created_at")
            if not created:
                continue

            date = datetime.fromisoformat(created.replace("Z", "+00:00"))

            if date >= cutoff:
                title = incident.get("name", "Untitled incident")
                status = incident.get("status", "unknown")
                found.append(f"{title} ({status})")

        return found, None
    except Exception:
        return [], "Incident information unavailable"


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()

    lines = [
        f"APPLICATION REPORT — {now:%Y-%m-%d %H:%M %Z}",
        "-" * 55
    ]

    for app in APPLICATIONS:
        website = website_status(app["website"])
        status = service_status(app["status"])
        incidents, error = recent_incidents(app["incidents"])

        lines.append(
            f"{app['name']}: Website {website} | Service: {status}"
        )

        if error:
            lines.append(f"  - {error}")
        elif incidents:
            for incident in incidents:
                lines.append(f"  - Recent incident: {incident}")
        else:
            lines.append("  - No published incidents found in the past 30 days")

        lines.append("  - Security breaches: Not checked")
        lines.append("")

    lines.append("-" * 55 + "\n")

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")

    print("Short report saved to:", LOG_FILE)


if __name__ == "__main__":
    main()
