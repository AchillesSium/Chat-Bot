from typing import Optional

import requests

from bot.helpers import YearWeek


Timeout = requests.Timeout


class AccessDenied(Exception):
    pass


class NotFound(Exception):
    pass


class Datasource:
    def __init__(self, api_base_url, api_key):
        self.base_url = api_base_url
        self.headers = {"x-api-key": api_key}

    def _get(self, route, params=None):
        url = self.base_url + route
        res = requests.get(url, params, headers=self.headers, timeout=5)
        if res.ok:
            return res.json()
        if res.status_code in (requests.codes.unauthorized, requests.codes.forbidden):
            raise AccessDenied(url, res.status_code)
        elif res.status_code == request.codes.not_found:
            raise NotFound(url)
        return {}

    def user_info(self, user_id):
        """
        returns dict: {
            "employeeId": int,
            "role": str,
            "skills": [str],
            "wishes": [str],
        }
        """
        try:
            return self._get(f"/user/{user_id}")
        except NotFound:
            return None

    def all_users(self):
        return {user["employeeId"]: user for user in self._get("/users")}

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
