from typing import Optional

import requests

from bot.helpers import YearWeek


class Datasource:
    def __init__(self, api_base_url, api_key):
        self.base_url = api_base_url
        self.headers = {"x-api-key": api_key}

    def _get(self, route, params=None):
        res = requests.get(self.base_url + route, params, headers=self.headers)
        return res.json() if res.ok else {}

    def user_info(self, user_id):
        """
        returns dict: {
            "employeeId": int,
            "role": str,
            "skills": [str],
            "wishes": [str],
        }
        """
        return self._get(f"/user/{user_id}")

    def all_users(self):
        return {user["employeeId"]: user for user in self._get("/users")}

    def user_allocations(self, user_id):
        return self._get(f"/user/{user_id}/allocations")

    def skills_by_user(self):
        """returns dict: {employeeId: [str]}"""
        return {info["employeeId"]: info["skills"] for info in self._get("/skills")}

    def allocations_within(self, start: YearWeek, end: Optional[YearWeek]):
        params = {"start": str(start)}
        if end:
            params["end"] = str(end)
        data = self._get("/allocations", params)
        return {
            entry["employeeId"]: entry["allocations"] for entry in data.get("users", ())
        }
