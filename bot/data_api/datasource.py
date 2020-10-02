from collections import namedtuple
from pathlib import Path

import json

# the parent of the git repository's root
DATA_DIR = Path(__file__).resolve(strict=True).parent.parent.parent.parent
PEOPLE_FILE = DATA_DIR / "people-simple.json"
ALLOCATION_FILE = DATA_DIR / "allocation.json"


YearWeek = namedtuple("YearWeek", ("year", "week"))


def parse_year_week(string):
    year, sep, week = string.partition("-W")
    if not sep:
        raise ValueError("invalid format")
    return YearWeek(int(year), int(week))


def parse_users(path: Path):
    # assuming one entry per line
    users = {}
    with path.open() as f:
        for line in f:
            user = json.loads(line)
            users[user["employeeId"]] = user
    return users


def parse_allocations(path: Path):
    # assuming one array
    with path.open() as f:
        raw = json.load(f)
    result = {}
    keys = ("id", "yearWeek", "percentage")
    for user in raw:
        user_id = user["user"]["employeeId"]
        allocations = []
        for project in user.get("projects", ()):
            allocations.extend(
                {key: alloc[key] for key in keys}
                for alloc in project.get("allocations", ())
            )
        allocations.sort(key=lambda item: item["yearWeek"])
        result[user_id] = allocations
    return result


class Datasource:
    def __init__(self):
        self.users = parse_users(PEOPLE_FILE)
        self.allocations = parse_allocations(ALLOCATION_FILE)

    def user_info(self, user_id):
        return self.users.get(user_id)

    def user_allocations(self, user_id):
        return self.allocations.get(user_id)

    def skills_by_user(self):
        return {user: info["skills"] for user, info in self.users.items()}

    def allocations_within(self, start, end):
        start = parse_year_week(start)
        end = parse_year_week(end)

        if start > end:
            return []

        def in_range(allocation):
            return start <= parse_year_week(allocation["yearWeek"]) <= end

        result = []
        for user, allocations in self.allocations.items():
            matching = list(filter(in_range, allocations))
            if matching:
                result.append(
                    {"employeeId": user, "allocations": matching,}
                )
        return result
