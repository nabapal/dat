#!/usr/bin/env python3

import argparse
import sqlite3
import csv
from datetime import datetime, timedelta
import sys
from typing import List

DEFAULT_DB = "/opt/dat/infra/db/activity_tracker.db"


def parse_team_tokens(raw: str) -> List[str]:
    return [t.strip() for t in raw.replace("/", ",").split(",") if t.strip()]


def qmarks(n: int) -> str:
    return ",".join(["?"] * n)


def get_team_rows(conn, team_names):
    cur = conn.execute(
        f"SELECT id, name FROM team WHERE name IN ({qmarks(len(team_names))})",
        tuple(team_names),
    )
    return cur.fetchall()


def get_user_ids_for_team_ids(conn, team_ids):
    cur = conn.execute(
        f"SELECT DISTINCT user_id FROM user_teams WHERE team_id IN ({qmarks(len(team_ids))})",
        tuple(team_ids),
    )
    return [r[0] for r in cur.fetchall()]


def find_activity_ids(conn, user_ids, cutoff):
    cur = conn.execute(
        f"""
        SELECT DISTINCT a.id
        FROM activity a
        LEFT JOIN activity_update au ON au.activity_id = a.id
        LEFT JOIN activity_assignees aa ON aa.activity_id = a.id
        WHERE (aa.user_id IN ({qmarks(len(user_ids))})
               OR au.updated_by IN ({qmarks(len(user_ids))}))
          AND (date(a.created_at) >= ?
               OR date(au.update_date) >= ?)
        """,
        tuple(user_ids) + tuple(user_ids) + (cutoff, cutoff),
    )
    return sorted({r[0] for r in cur.fetchall()})


def get_activity_details(conn, aid):
    cur = conn.execute(
        """
        SELECT id, activity_id, details, activity_type, status
        FROM activity WHERE id = ?
        """,
        (aid,),
    )
    r = cur.fetchone()
    if not r:
        return None
    return {
        "pk": r[0],
        "activity_code": r[1],
        "details": r[2],
        "type": r[3],
        "status": r[4],
    }


def get_recent_updates(conn, aid, cutoff):
    cur = conn.execute(
        """
        SELECT update_date, update_text
        FROM activity_update
        WHERE activity_id = ?
          AND date(update_date) >= ?
        ORDER BY update_date ASC
        """,
        (aid, cutoff),
    )
    return cur.fetchall()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--teams", required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--csv", default=None)
    args = p.parse_args()

    cutoff = (datetime.now() - timedelta(days=args.days)).date().isoformat()

    conn = sqlite3.connect(args.db)

    teams = get_team_rows(conn, parse_team_tokens(args.teams))
    team_ids = [t[0] for t in teams]

    user_ids = get_user_ids_for_team_ids(conn, team_ids)
    activity_ids = find_activity_ids(conn, user_ids, cutoff)

    rows = []
    sr_no = 1

    for aid in activity_ids:
        act = get_activity_details(conn, aid)
        if not act:
            continue

        updates = get_recent_updates(conn, aid, cutoff)

        update_text = "\n".join(
            [f"{i+1}. {u[1]}" for i, u in enumerate(updates)]
        ) if updates else "No updates this week"

        rows.append([
            sr_no,
            act["activity_code"],
            f"{act['type']} - {act['details']}",
            update_text,
            act["status"],
            ""
        ])
        sr_no += 1

    # ---------- PRINT TABLE ----------
    headers = [
        "Sr No",
        "Project ID / Tracker ID",
        "Description",
        "Current Week Activities in the Project",
        "Project Status",
        "CLM ID",
    ]

    print("\nWEEKLY PROJECT UPDATE\n")
    print("-" * 140)
    print("{:<6} {:<25} {:<40} {:<45} {:<10} {:<8}".format(*headers))
    print("-" * 140)

    for r in rows:
        print("{:<6} {:<25} {:<40} {:<45} {:<10} {:<8}".format(
            r[0], r[1], r[2][:38], r[3][:43], r[4], r[5]
        ))

    print("-" * 140)

    # ---------- CSV EXPORT ----------
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"\nCSV written to: {args.csv}")

    conn.close()


if __name__ == "__main__":
    main()
