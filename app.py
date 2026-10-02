import sqlite3
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, g, abort

import provisioning_simulator as prov

DB_PATH = "desksupport.db"
SLA_HOURS_BY_PRIORITY = {"Critical": 4, "High": 8, "Medium": 24, "Low": 72}
CATEGORIES = ["Hardware", "Software", "Network", "Account"]
REVIEW_DUE_DAYS = 90

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open("schema.sql") as f:
        conn.executescript(f.read())
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hours_open(created_at, resolved_at=None):
    start = datetime.fromisoformat(created_at)
    end = datetime.fromisoformat(resolved_at) if resolved_at else datetime.now(timezone.utc)
    return round((end - start).total_seconds() / 3600, 1)


def days_since(iso):
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).days


def decorate_article(row):
    a = dict(row)
    votes = a["helpful_votes"] + a["unhelpful_votes"]
    a["helpful_pct"] = round(a["helpful_votes"] / votes * 100) if votes else None
    a["days_since_update"] = days_since(a["updated_at"])
    a["review_due"] = a["status"] == "Published" and a["days_since_update"] > REVIEW_DUE_DAYS
    return a


def kb_gap_report(db):
    """Per category: ticket volume vs published article coverage.
    A category with tickets and no published article is a shift left opportunity."""
    report = []
    for cat in CATEGORIES:
        tickets = db.execute("SELECT COUNT(*) c FROM tickets WHERE category = ?", (cat,)).fetchone()["c"]
        linked = db.execute(
            "SELECT COUNT(*) c FROM tickets WHERE category = ? AND article_id IS NOT NULL", (cat,)
        ).fetchone()["c"]
        published = db.execute(
            "SELECT COUNT(*) c FROM kb_articles WHERE category = ? AND status = 'Published'", (cat,)
        ).fetchone()["c"]
        report.append({
            "category": cat,
            "tickets": tickets,
            "linked": linked,
            "published": published,
            "coverage_pct": round(linked / tickets * 100) if tickets else 0,
            "gap": tickets > 0 and published == 0,
        })
    return report


@app.route("/")
def index():
    db = get_db()
    status_filter = request.args.get("status", "all")
    if status_filter == "all":
        rows = db.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC", (status_filter,)
        ).fetchall()

    tickets = []
    for r in rows:
        t = dict(r)
        age = hours_open(t["created_at"], t["resolved_at"])
        sla_limit = SLA_HOURS_BY_PRIORITY.get(t["priority"], 24)
        t["age_hours"] = age
        t["sla_breached"] = t["status"] != "Resolved" and age > sla_limit
        tickets.append(t)

    return render_template("index.html", tickets=tickets, status_filter=status_filter)


@app.route("/tickets/new", methods=["GET", "POST"])
def new_ticket():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO tickets (requester_name, department, category, priority, description, "
            "status, assigned_to, created_at) VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)",
            (
                request.form["requester_name"],
                request.form["department"],
                request.form["category"],
                request.form["priority"],
                request.form["description"],
                request.form.get("assigned_to") or "Unassigned",
                now_iso(),
            ),
        )
        db.commit()
        return redirect(url_for("index"))
    return render_template("new_ticket.html")


@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)
    articles = db.execute(
        "SELECT id, title, category FROM kb_articles WHERE status = 'Published' ORDER BY category, title"
    ).fetchall()
    linked = None
    if ticket["article_id"]:
        linked = db.execute("SELECT id, title FROM kb_articles WHERE id = ?", (ticket["article_id"],)).fetchone()
    return render_template("ticket_detail.html", ticket=dict(ticket), articles=articles, linked=linked)


@app.route("/tickets/<int:ticket_id>/resolve", methods=["POST"])
def resolve_ticket(ticket_id):
    db = get_db()
    article_id = request.form.get("article_id") or None
    first_contact = 1 if request.form.get("first_contact") else 0
    db.execute(
        "UPDATE tickets SET status = 'Resolved', resolved_at = ?, article_id = ?, first_contact = ? WHERE id = ?",
        (now_iso(), article_id, first_contact, ticket_id),
    )
    db.commit()
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.route("/kb")
def kb_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "all")

    sql = "SELECT * FROM kb_articles WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR body LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category != "all":
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY updated_at DESC"

    articles = [decorate_article(r) for r in db.execute(sql, params).fetchall()]
    return render_template("kb_list.html", articles=articles, q=q, category=category, categories=CATEGORIES)


@app.route("/kb/new", methods=["GET", "POST"])
def kb_new():
    if request.method == "POST":
        db = get_db()
        ts = now_iso()
        cur = db.execute(
            "INSERT INTO kb_articles (title, category, source_policy, body, status, version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                request.form["title"],
                request.form["category"],
                request.form.get("source_policy") or None,
                request.form["body"],
                request.form["status"],
                ts,
                ts,
            ),
        )
        db.commit()
        return redirect(url_for("kb_detail", article_id=cur.lastrowid))
    return render_template("kb_form.html", article=None, categories=CATEGORIES)


@app.route("/kb/<int:article_id>")
def kb_detail(article_id):
    db = get_db()
    row = db.execute("SELECT * FROM kb_articles WHERE id = ?", (article_id,)).fetchone()
    if row is None:
        abort(404)
    db.execute("UPDATE kb_articles SET view_count = view_count + 1 WHERE id = ?", (article_id,))
    db.commit()
    row = db.execute("SELECT * FROM kb_articles WHERE id = ?", (article_id,)).fetchone()
    return render_template("kb_detail.html", article=decorate_article(row))


@app.route("/kb/<int:article_id>/edit", methods=["GET", "POST"])
def kb_edit(article_id):
    db = get_db()
    row = db.execute("SELECT * FROM kb_articles WHERE id = ?", (article_id,)).fetchone()
    if row is None:
        abort(404)
    if request.method == "POST":
        db.execute(
            "UPDATE kb_articles SET title = ?, category = ?, source_policy = ?, body = ?, status = ?, "
            "version = version + 1, updated_at = ? WHERE id = ?",
            (
                request.form["title"],
                request.form["category"],
                request.form.get("source_policy") or None,
                request.form["body"],
                request.form["status"],
                now_iso(),
                article_id,
            ),
        )
        db.commit()
        return redirect(url_for("kb_detail", article_id=article_id))
    return render_template("kb_form.html", article=dict(row), categories=CATEGORIES)


@app.route("/kb/<int:article_id>/vote", methods=["POST"])
def kb_vote(article_id):
    db = get_db()
    column = "helpful_votes" if request.form.get("vote") == "helpful" else "unhelpful_votes"
    db.execute(f"UPDATE kb_articles SET {column} = {column} + 1 WHERE id = ?", (article_id,))
    db.commit()
    return redirect(url_for("kb_detail", article_id=article_id))


@app.route("/dashboard")
def dashboard():
    db = get_db()
    rows = [dict(r) for r in db.execute("SELECT * FROM tickets").fetchall()]

    total = len(rows)
    open_count = sum(1 for t in rows if t["status"] != "Resolved")
    resolved = [t for t in rows if t["status"] == "Resolved"]
    resolved_count = len(resolved)

    if resolved:
        avg_resolution = round(
            sum(hours_open(t["created_at"], t["resolved_at"]) for t in resolved) / len(resolved), 1
        )
        fcr_rate = round(sum(1 for t in resolved if t["first_contact"]) / len(resolved) * 100, 1)
        kb_linked_pct = round(sum(1 for t in resolved if t["article_id"]) / len(resolved) * 100, 1)
    else:
        avg_resolution = fcr_rate = kb_linked_pct = 0

    by_category = {}
    for t in rows:
        by_category[t["category"]] = by_category.get(t["category"], 0) + 1

    breaches = sum(
        1 for t in rows
        if t["status"] != "Resolved" and hours_open(t["created_at"]) > SLA_HOURS_BY_PRIORITY.get(t["priority"], 24)
    )

    articles = [decorate_article(r) for r in db.execute("SELECT * FROM kb_articles").fetchall()]
    review_due = [a for a in articles if a["review_due"]]
    gaps = kb_gap_report(db)

    return render_template(
        "dashboard.html",
        total=total,
        open_count=open_count,
        resolved_count=resolved_count,
        avg_resolution=avg_resolution,
        by_category=by_category,
        breaches=breaches,
        fcr_rate=fcr_rate,
        kb_linked_pct=kb_linked_pct,
        review_due=review_due,
        gaps=gaps,
    )


@app.route("/provisioning", methods=["GET", "POST"])
def provisioning():
    result = None
    if request.method == "POST":
        result = prov.run_new_hire_workflow(
            request.form["full_name"], request.form["department"], request.form["device_tag"]
        )

    db = get_db()
    logs = db.execute("SELECT * FROM provisioning_log ORDER BY id DESC LIMIT 30").fetchall()
    return render_template("provisioning.html", result=result, logs=logs, departments=list(prov.DEPARTMENTS_TO_GROUPS.keys()))


if __name__ == "__main__":
    import os

    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True, port=5000)
