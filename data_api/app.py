"""
A mock data interface and api for the bot.

Endpoints:

/user/<id>
  {
    "employeeId": int,
    "role": str,
    "skills": [str],
    "wishes": [str],
  }

/user/<id>/allocations
  {
    "employeeId": int,
    "allocations": [Allocation],
  }

/allocations?start=<YearWeek>&end=<YearWeek>
  {
    "startYearWeek": str,
    "endYearWeek": str,
    "users": [
      {
        "employeeId": int,
        "allocations": [Allocation],
      }
    ]
  }


Allocation
  {
    "id": int,
    "percentage": int,
    "yearWeek": str,  # e.g. 2020-W40
  }
"""

from flask import Flask, jsonify, request

from .datasource import Datasource

source = Datasource()

app = Flask(__name__)


@app.route("/user/<int:user_id>")
def user(user_id):
    "Return info of the user (e.g. skills, wishes)"
    data = source.user_info(user_id)
    if data is None:
        return {}, 404
    return data


@app.route("/user/<int:user_id>/allocations")
def user_allocations(user_id):
    "Return allocation of the user"
    data = source.user_allocations(user_id)
    if data is None:
        return {}, 404
    return {
        "employeeId": 1,
        "allocations": data,
    }


@app.route("/allocations")
def allocations():
    start = request.args.get("start")
    end = request.args.get("end")
    if start is None or end is None:
        return {"error": "missing parameters"}, 400
    try:
        data = source.allocations_within(start, end)
    except ValueError:
        return {"error": "invalid parameters"}, 400
    return {
        "startYearWeek": start,
        "endYearWeek": end,
        "users": data,
    }


@app.route("/user/example")
def example_user():
    return {
        "employeeId": 1,
        # "slack_username": "@example_user",
        "role": "Developer (Example)",
        "skills": ["database", "internet explorer", "Web programming"],
        "wishes": [
            "I'd like to work on the very fullest stack available, but not overflowing it"
        ],
    }


@app.route("/user/example/allocations")
def example_user_allocations():
    return {
        "employeeId": 1,
        "allocations": [
            {"id": 12345, "percentage": 100, "yearWeek": "2020-W47",},
            {"id": 1234, "percentage": 100, "yearWeek": "2020-W48",},
            {"id": 1234, "percentage": 100, "yearWeek": "2020-W49",},
            {"id": 1234, "percentage": 100, "yearWeek": "2020-W50",},
        ],
    }


@app.route("/allocations/example")
def example_allocations():
    return {
        "startYearWeek": "2020-W47",
        "endYearWeek": "2020-W50",
        "users": [
            {
                "employeeId": 1,
                "allocations": [
                    {"id": 12345, "percentage": 100, "yearWeek": "2020-W47",},
                    {"id": 1234, "percentage": 100, "yearWeek": "2020-W48",},
                    {"id": 1234, "percentage": 100, "yearWeek": "2020-W49",},
                ],
            },
            {
                "employeeId": 2,
                "allocations": [
                    {"id": 1234, "percentage": 100, "yearWeek": "2020-W50",},
                ],
            },
        ],
    }


if __name__ == "__main__":
    app.run()
