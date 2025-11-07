#!/usr/bin/env python3
"""Quick report preview for weekly/monthly activity snapshots.

This helper lets super leads or team leads inspect the SQLite database
and review activity/update counts for a specific week or month before
adding the filters to the web UI.
"""
import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy.orm import joinedload

from app import app
from app.models import Activity, ActivityUpdate, Team, User


def _time_window(period: str, value: int, year: int):
    """Return inclusive start date and exclusive end date for the window."""
    if period == "week":
        try:
            start = datetime.fromisocalendar(year, value, 1)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO week {value} for year {year}") from exc
        end = start + timedelta(days=7)
    elif period == "month":
        if value < 1 or value > 12:
            raise ValueError("Month must be between 1 and 12")
        start = datetime(year, value, 1)
        next_month_year = year + (1 if value == 12 else 0)
        next_month = 1 if value == 12 else value + 1
        end = datetime(next_month_year, next_month, 1)
    else:
        raise ValueError("Period must be 'week' or 'month'")
    return start, end


def _team_filter_clause(team_name: str):
    if not team_name:
        return None
    team = Team.query.filter(Team.name.ilike(team_name)).first()
    if not team:
        raise ValueError(f"Team '{team_name}' not found")
    return team


def summarize(period: str, value: int, year: int, team_name: Optional[str]):
    start_dt, end_dt = _time_window(period, value, year)
    start_date = start_dt.date()
    end_date = (end_dt - timedelta(days=1)).date()

    team = _team_filter_clause(team_name)

    # Build lookup upfront to avoid repetitive queries when checking teams
    users = (
        User.query.options(joinedload(User.teams))
        .order_by(User.username)
        .all()
    )
    user_lookup = {u.id: u for u in users}

    def _user_in_scope(user: User) -> bool:
        if not team:
            return user.role in {"team_lead", "super_lead", "member"}
        return any(t.id == team.id for t in user.teams)

    # Activities within the window (start_date inclusive, end exclusive)
    activities = (
        Activity.query
        .filter(Activity.start_date >= start_dt)
        .filter(Activity.start_date < end_dt)
        .all()
    )

    summary = defaultdict(lambda: {
        "activities": 0,
        "statuses": defaultdict(int),
        "updates": 0,
        "activity_ids": set(),
    })

    for activity in activities:
        for assignee in activity.assignees.all():
            if not _user_in_scope(assignee):
                continue
            data = summary[assignee.username]
            data["activities"] += 1
            data["statuses"][activity.status or "unknown"] += 1
            data["activity_ids"].add(activity.activity_id)

    # Updates (ActivityUpdate.update_date is a Date column)
    updates = (
        ActivityUpdate.query
        .filter(ActivityUpdate.update_date >= start_date)
        .filter(ActivityUpdate.update_date <= end_date)
        .all()
    )

    for update in updates:
        user = user_lookup.get(update.updated_by)
        if not user or not _user_in_scope(user):
            continue
        data = summary[user.username]
        data["updates"] += 1
        data["activity_ids"].add(str(update.activity_id))

    return {
        "period": period,
        "value": value,
        "year": year,
        "start": start_dt,
        "end": end_dt,
        "team": team.name if team else None,
        "summary": summary,
    }


def format_summary(result):
    header = ["User", "Activities", "Updates", "Status counts", "Activity IDs"]
    lines = [" | ".join(header)]
    lines.append("-" * len(lines[0]))

    for username in sorted(result["summary"].keys()):
        data = result["summary"][username]
        status_bits = ", ".join(
            f"{status}:{count}" for status, count in sorted(data["statuses"].items())
        ) or "(none)"
        activity_ids = ", ".join(sorted(data["activity_ids"])) or "(none)"
        lines.append(
            f"{username:<18} | {data['activities']:>10} | {data['updates']:>7} | "
            f"{status_bits:<40} | {activity_ids}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Preview weekly/monthly activity snapshots.")
    parser.add_argument("period", choices=["week", "month"], help="Period to inspect")
    parser.add_argument("value", type=int, help="Week number (1-53) or month (1-12)")
    parser.add_argument("year", type=int, help="Calendar year for the selection")
    parser.add_argument("--team", dest="team", help="Optional team name filter (case-insensitive)")
    args = parser.parse_args()

    with app.app_context():
        result = summarize(args.period, args.value, args.year, args.team)
        print(
            f"Snapshot for {result['period']} {result['value']} in {result['year']} "
            f"({result['start'].date()} → {(result['end'] - timedelta(days=1)).date()})"
        )
        if result["team"]:
            print(f"Filtered team: {result['team']}")
        print()
        if not result["summary"]:
            print("No activities or updates found for the requested window.")
        else:
            print(format_summary(result))


if __name__ == "__main__":
    main()
