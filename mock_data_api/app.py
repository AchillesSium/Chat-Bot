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

/users
  [
    {
      "employeeId": int,
      "role": str,
      "skills": [str],
      "wishes": [str],
    }
  ]

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

/skills
  [
    {
      "employeeId": int,
      "skills": [str],
    }
  ]


Allocation
  {
    "id": int,
    "percentage": int,
    "yearWeek": str,  # e.g. 2020-W40
  }
"""

from flask import Flask, jsonify, request

from datasource import Datasource

source = Datasource()


app = Flask(__name__)


@app.before_request
def require_api_key():
    print("key:", request.headers.get("x-api-key"))
    if request.headers.get("x-api-key") != "open sesame":
        return "You shall not pass", 401


@app.route("/user/<int:user_id>")
def user(user_id):
    "Return info of the user (e.g. skills, wishes)"
    data = source.user_info(user_id)
    if data is None:
        return {}, 404
    return data


@app.route("/users")
def users():
    "Return info of all user"
    return jsonify(source.all_users())


@app.route("/skills")
def skills():
    raw = source.skills_by_user()
    data = [{"employeeId": user, "skills": skills} for user, skills in raw.items()]
    return jsonify(data)


@app.route("/allocations")
def allocations():
    start = request.args.get("start")
    end = request.args.get("end")
    if start is None:
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
    app.run(host="0.0.0.0", port=80)
