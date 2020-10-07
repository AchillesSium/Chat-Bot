from typing import NamedTuple, Optional

from bot.data_api.datasource import Datasource
from bot.recommenders.skill_recommender import SkillRecommendation, SkillRecommenderCF


class User(NamedTuple):
    id: str
    employee_id: int
    # Whatever other fields we need
    previous_time: Optional[int] = None
    previous_recommendation: Optional[SkillRecommendation] = None


class Bot:
    def __init__(self, user_db=None, data_source=None):
        self.user_db = user_db or InMemoryDb()
        self.data_source = data_source or Datasource()
        self.recommender = SkillRecommenderCF()

    def help(self):
        return {
            "response_type": "ephemeral",
            "text": "Example help message:\nTo enrol, send me a message like: 'enrol <employee_id>'",
        }

    def enrol_user(self, user_id, employee_id):
        def response(**kw):
            return {
                "response_type": "ephemeral",
                **kw,
            }

        if self.data_source.user_info(employee_id) is None:
            return response(
                text=f"Hmm... There is no record for the employee id: {employee_id}"
            )

        user = User(user_id, employee_id)
        try:
            self.user_db.add_user(user)
        except KeyError:
            return response(text="You are already enrolled!")

        rec = self.recommender.recommend_skills_to_user(employee_id)
        skills = "\n".join(f"- {r}" for r in rec.recommendation_list)
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Success!* You are now enrolled"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "We found these skills similar to yours:\n" + skills,
                },
            },
        ]
        return response(blocks=blocks)


class InMemoryDb:
    def __init__(self):
        self.users = {}

    def add_user(self, user: User):
        if user.id in self.users:
            raise KeyError("user exists")
        self.users[user.id] = user

    def find_user(self, user_id: str):
        return self.users[user_id]
