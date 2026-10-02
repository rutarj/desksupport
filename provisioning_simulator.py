"""
provisioning_simulator.py

Simulates the account and device provisioning steps an IT service desk
performs when onboarding a user or imaging a machine: Active Directory
account creation, security group assignment, and Intune device enrollment.

This is a local simulation (no real Azure AD or Intune tenant is called).
Every action is logged to the provisioning_log table so the flow can be
demonstrated end to end, including realistic failure/compliance states.
"""
import random
import sqlite3
from datetime import datetime, timezone

DB_PATH = "desksupport.db"

DEPARTMENTS_TO_GROUPS = {
    "Finance": ["GRP-Finance-Users", "GRP-VPN-Access"],
    "IT": ["GRP-IT-Admins", "GRP-VPN-Access", "GRP-ServiceDesk-Tools"],
    "Operations": ["GRP-Ops-Users"],
    "HR": ["GRP-HR-Users", "GRP-Confidential-Share"],
}

COMPLIANCE_CHECKS = [
    "Disk encryption enabled",
    "OS version up to date",
    "Antivirus definitions current",
    "Password policy applied",
]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _log(conn, action_type, target, detail, status):
    conn.execute(
        "INSERT INTO provisioning_log (action_type, target, detail, status, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (action_type, target, detail, status, datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    conn.commit()


def create_ad_user(full_name, department):
    """Simulates creating an Active Directory account for a new hire."""
    conn = _connect()
    username = (full_name.split()[0][0] + full_name.split()[-1]).lower()
    upn = f"{username}@desksupportlab.local"
    _log(conn, "AD_USER_CREATE", upn, f"Created AD account for {full_name} in {department} OU", "Success")

    groups = DEPARTMENTS_TO_GROUPS.get(department, ["GRP-General-Users"])
    for group in groups:
        _log(conn, "AD_GROUP_ASSIGN", upn, f"Added to security group {group}", "Success")

    conn.close()
    return {"username": username, "upn": upn, "groups": groups}


def enroll_device(device_tag, assigned_user_upn):
    """Simulates Intune enrollment and a post enrollment compliance check."""
    conn = _connect()
    _log(conn, "INTUNE_ENROLL", device_tag, f"Device enrolled and assigned to {assigned_user_upn}", "Success")

    failed_check = random.choice(COMPLIANCE_CHECKS) if random.random() < 0.25 else None
    for check in COMPLIANCE_CHECKS:
        if check == failed_check:
            _log(conn, "INTUNE_COMPLIANCE", device_tag, f"{check}: FAILED", "Non-Compliant")
        else:
            _log(conn, "INTUNE_COMPLIANCE", device_tag, f"{check}: passed", "Success")

    conn.close()
    return {"device_tag": device_tag, "compliant": failed_check is None, "failed_check": failed_check}


def run_new_hire_workflow(full_name, department, device_tag):
    """End to end simulation: AD account, group assignment, device enrollment."""
    ad_result = create_ad_user(full_name, department)
    device_result = enroll_device(device_tag, ad_result["upn"])
    return {"ad": ad_result, "device": device_result}
