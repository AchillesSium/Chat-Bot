import requests


class Datasource:
    def __init__(self, api_base_url, api_key):
        self.base_url = api_base_url
        self.headers = {"x-api-key": api_key}

    def _get(self, route):
        res = requests.get(self.base_url + route, headers=self.headers)
        return res.json()

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

    def user_allocations(self, user_id):
        return self._get(f"/user/{user_id}/allocations")

    def skills_by_user(self):
        """returns dict: {employeeId: [str]}"""
        return {info["employeeId"]: info["skills"] for info in self._get("/skills")}

    def allocations_within(self, start, end):
        return self._get("/allocations", {"start": start, "end": end}).get("users")
