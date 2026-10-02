"""
test_kb.py

Tests for the knowledge base module: authoring, versioned updates, review due
flags, helpful votes, first contact resolution, and the knowledge gap report.
Run with: python -m pytest test_kb.py
"""
import os
import tempfile

import pytest

import app as desk
import seed_data


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    desk.DB_PATH = path
    desk.init_db()
    seed_data.seed(path)
    yield desk.app.test_client()
    os.remove(path)


def test_new_article_starts_at_version_one(client):
    r = client.post("/kb/new", data={
        "title": "Test article", "category": "Software", "source_policy": "Test Policy",
        "body": "Step one.", "status": "Published"}, follow_redirects=True)
    assert r.status_code == 200
    assert b"v1" in r.data


def test_editing_article_increments_version(client):
    client.post("/kb/1/edit", data={
        "title": "Reset a locked user account", "category": "Account", "source_policy": "Policy",
        "body": "Updated steps.", "status": "Published"})
    r = client.get("/kb/1")
    assert b"v2" in r.data
    assert b"Updated steps." in r.data


def test_old_article_flagged_review_due(client):
    r = client.get("/kb")
    assert b"Review due" in r.data  # the 120 day old shared mailbox article


def test_helpful_vote_recorded(client):
    client.post("/kb/1/vote", data={"vote": "helpful"})
    r = client.get("/kb/1")
    assert b"Yes (5)" in r.data


def test_search_finds_article_by_body_text(client):
    r = client.get("/kb?q=VPN")
    assert b"Connect to the company VPN" in r.data
    assert b"Reset a locked user account" not in r.data


def test_gap_report_flags_category_without_published_article(client):
    with desk.app.app_context():
        db = desk.get_db()
        report = {row["category"]: row for row in desk.kb_gap_report(db)}
    assert report["Software"]["gap"] is True   # only a Draft article exists for Software
    assert report["Account"]["gap"] is False


def test_publishing_article_closes_the_gap(client):
    client.post("/kb/6/edit", data={
        "title": "Install approved software", "category": "Software", "source_policy": "Software Installation Standard",
        "body": "Published steps.", "status": "Published"})
    with desk.app.app_context():
        db = desk.get_db()
        report = {row["category"]: row for row in desk.kb_gap_report(db)}
    assert report["Software"]["gap"] is False


def test_resolving_ticket_links_article_and_records_first_contact(client):
    client.post("/tickets/10/resolve", data={"article_id": "3", "first_contact": "on"})
    r = client.get("/tickets/10")
    assert b"Connect to the company VPN" in r.data
    assert b"Yes" in r.data


def test_dashboard_reports_first_contact_resolution_rate(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"First Contact Resolution" in r.data
    assert b"Knowledge Gap Report" in r.data
