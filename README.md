# DeskSupport: IT Service Desk Simulation and Ticket Management

A small Flask app that simulates the day to day work of an IT service desk:
logging tickets, tracking them against SLA targets, and provisioning new
hire accounts and devices the way a real enterprise service desk would.

## Why this exists

Built to demonstrate, with real working code, the kind of end user support
and IT operations workflow described in service desk and IT analyst job
postings: ticket triage, SLA tracking, and account/device provisioning.

## Features

- **Ticket management** — create, view, filter, and resolve tickets by
  category (Hardware, Software, Network, Account), priority, and department.
- **SLA tracking** — each priority level has an SLA window (Critical: 4h,
  High: 8h, Medium: 24h, Low: 72h). Tickets that exceed their window while
  still open are flagged as breached, both in the ticket list and on the
  dashboard.
- **Dashboard** — total, open, and resolved ticket counts, average
  resolution time, ticket volume by category, and a live SLA breach count.
- **Knowledge base** — write, search, version, and retire support articles.
  Each article records the source policy it was written from, a status
  (Draft, Published, Retired), a version number that increments on every
  edit, view counts, and helpful or not helpful votes. Articles not updated
  in 90 days are flagged as review due.
- **First contact resolution** — when a ticket is resolved, the agent can
  link the knowledge article used and mark whether it was resolved on first
  contact. The dashboard reports the first contact resolution rate and the
  share of tickets resolved with an article.
- **Knowledge gap report** — compares ticket volume against published
  articles per category. A category with tickets and no published article
  is flagged as a shift left opportunity.
- **Provisioning simulator** — simulates the Active Directory account
  creation, security group assignment, and Intune device enrollment steps
  used to onboard a new hire, including a randomized compliance check so
  the log reflects realistic pass/fail outcomes. No real Azure or Intune
  tenant is called; every action is logged to a local table so the flow
  can be walked through end to end.

## Tech stack

Python, Flask, SQLite, Bootstrap (CDN).

## Setup

```
pip install -r requirements.txt
python seed_data.py   # optional: sample articles and tickets
python app.py
```

Visit `http://localhost:5000`. The database is created automatically on
first run.

## Tests

```
python -m pytest test_kb.py
```

## Project structure

```
app.py                     Flask routes and SLA/dashboard logic
provisioning_simulator.py  AD/Intune style provisioning simulation
seed_data.py               Synthetic sample articles and tickets
test_kb.py                 Tests for the knowledge base module
schema.sql                 SQLite schema for tickets and provisioning_log
templates/                 Jinja2 templates (Bootstrap styled)
```

## Notes

Knowledge articles and tickets in `seed_data.py` are synthetic content written for this project.

This is a portfolio project built to demonstrate service desk and IT
operations concepts, not a connection to a real Active Directory or
Intune tenant.
