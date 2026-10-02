"""
seed_data.py

Loads sample knowledge base articles and tickets so the dashboard, gap report,
and review due flags have something to show. All content is synthetic and
written for this project.

Run with: python seed_data.py
"""
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "desksupport.db"

ARTICLES = [
    ("Reset a locked user account", "Account", "Account Access and Password Policy", "Published", 12,
     "1. Confirm the requester identity using two verification questions.\n2. Open the directory console and find the account.\n3. Unlock the account and force a password reset at next sign in.\n4. Confirm the requester can sign in, then close the ticket."),
    ("Set up a shared mailbox", "Account", "Shared Resource Access Standard", "Published", 120,
     "1. Confirm the request is approved by the mailbox owner.\n2. Create the shared mailbox.\n3. Add approved members with the correct permission level.\n4. Send the mailbox address to the requester."),
    ("Connect to the company VPN", "Network", "Remote Access Policy", "Published", 8,
     "1. Confirm the device is enrolled and compliant.\n2. Install the approved VPN client.\n3. Sign in with the corporate account and approve the second factor prompt.\n4. Confirm access to an internal site."),
    ("Laptop will not start: first checks", "Hardware", "Endpoint Support Procedure", "Published", 20,
     "1. Confirm the charger and power outlet work.\n2. Hold the power button for 15 seconds, then restart.\n3. Disconnect all peripherals and retry.\n4. If it still fails, log a hardware ticket and arrange a loaner device."),
    ("Printer shows offline", "Hardware", "Endpoint Support Procedure", "Published", 15,
     "1. Confirm the printer is powered and on the network.\n2. Remove and re-add the printer on the workstation.\n3. Print a test page.\n4. Escalate to the network team if the printer is unreachable."),
    ("Install approved software", "Software", "Software Installation Standard", "Draft", 3,
     "Draft: steps for requesting and installing approved software through the company portal."),
]

# (requester, dept, category, priority, description, hours_to_resolve or None, article_index or None, first_contact)
TICKETS = [
    ("A. Khan", "Finance", "Account", "High", "Account locked after failed sign in", 1, 0, 1),
    ("B. Lee", "HR", "Account", "Medium", "Need a shared mailbox for onboarding", 6, 1, 0),
    ("C. Diaz", "IT", "Network", "Medium", "Cannot connect to VPN from home", 2, 2, 1),
    ("D. Patel", "Operations", "Hardware", "High", "Laptop will not turn on", 5, 3, 0),
    ("E. Novak", "Finance", "Hardware", "Low", "Printer offline on floor 3", 3, 4, 1),
    ("F. Osei", "Operations", "Software", "Medium", "Need design software installed", 20, None, 0),
    ("G. Tran", "HR", "Software", "Low", "Spreadsheet add in will not load", 30, None, 0),
    ("H. Silva", "Finance", "Software", "Medium", "Approved software not in portal", 9, None, 0),
    ("I. Brown", "IT", "Account", "Critical", "Executive account locked", 1, 0, 1),
    ("J. Chen", "Operations", "Network", "High", "VPN drops every hour", None, None, 0),
    ("K. Ali", "HR", "Hardware", "Medium", "Docking station not detected", None, None, 0),
    ("L. Moore", "Finance", "Software", "Low", "Software update prompt keeps returning", None, None, 0),
]


def seed(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc)

    article_ids = []
    for title, cat, policy, status, days_old, body in ARTICLES:
        ts = (now - timedelta(days=days_old)).isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO kb_articles (title, category, source_policy, body, status, version, view_count, "
            "helpful_votes, unhelpful_votes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (title, cat, policy, body, status, 10 + days_old % 7, 4, 1, ts, ts),
        )
        article_ids.append(cur.lastrowid)

    for i, (req, dept, cat, pri, desc, hours, art_idx, fc) in enumerate(TICKETS):
        created = now - timedelta(hours=(hours or 0) + 30 + i * 3)
        resolved = (created + timedelta(hours=hours)).isoformat(timespec="seconds") if hours else None
        conn.execute(
            "INSERT INTO tickets (requester_name, department, category, priority, description, status, "
            "assigned_to, created_at, resolved_at, article_id, first_contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (req, dept, cat, pri, desc, "Resolved" if hours else "Open", "Service Desk",
             created.isoformat(timespec="seconds"), resolved,
             article_ids[art_idx] if art_idx is not None else None, fc),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import os
    if not os.path.exists(DB_PATH):
        import app
        app.init_db()
    seed()
    print("Seeded sample articles and tickets.")
