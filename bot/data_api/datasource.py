from collections import namedtuple
from pathlib import Path

import json

# the parent of the git repository's root
DATA_DIR = Path(__file__).resolve(strict=True).parent.parent.parent.parent
PEOPLE_FILE = DATA_DIR / "people-simple.json"
ALLOCATION_FILE = DATA_DIR / "allocation.json"


YearWeek = namedtuple("YearWeek", ("year", "week"))


def parse_year_week(string):
    """ Parse year-week pair into a named YearWeek tuple.
    Yearweek string is expected to be in yyyy-Www

    @param string: Year-week pair as string
    @return: Year-week pair as YearWeek
    """
    year, sep, week = string.partition("-W")
    if not sep:
        raise ValueError("invalid format")
    return YearWeek(int(year), int(week))


def parse_users(path: Path):
    """ Parse user data json to json.
    Assumes the data file to be as given by customer, i.e. unmodified.
    That is,

    @param path: User data file path
    @return: User data as JSON
    """
    users = {}
    with path.open(encoding="utf-8") as f:
        user_dict = ""
        for line in f:
            if line.startswith("}"):
                user_dict += "}"
                user = json.loads(user_dict)
                users[user["employeeId"]] = user
                user_dict = ""
            else:
                user_dict += line
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
        """
        returns dict: {
            "employeeId": int,
            "role": str,
            "skills": [str],
            "wishes": [str],
        }
        """
        return self.users.get(user_id)

    def user_allocations(self, user_id):
        return self.allocations.get(user_id)

    def skills_by_user(self):
        """returns dict: {employeeId: [str]}"""
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


if __name__ == "__main__":
    # For debugging
    ds = Datasource()

    print("Breakpoint here")
