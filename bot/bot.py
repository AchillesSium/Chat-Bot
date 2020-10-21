from typing import NamedTuple, Optional, Callable

from bot.data_api.datasource import Datasource
from bot.recommenders.skill_recommender import SkillRecommendation, SkillRecommenderCF
from bot.chatBotDatabase import BotDatabase


class User(NamedTuple):
    id: str
    employee_id: int


class Bot:
    def __init__(
        self,
        send_message: Callable[[str, dict], bool],
        user_db: Optional[BotDatabase] = None,
        data_source: Optional[Datasource] = None,
    ):
        self.send_message = send_message
        self.user_db: BotDatabase = user_db or BotDatabase(":memory:")
        self.data_source: Datasource = data_source or Datasource()
        self.recommender = SkillRecommenderCF(self.data_source)

    def help(self):
        return {
            "text": "Example help message:\nTo enrol, send me a message like: 'enrol <employee_id>'",
        }

    def enrol_user(self, user_id: str, employee_id: int):
        if self.data_source.user_info(employee_id) is None:
            return {
                "text": f"Hmm... There is no record for the employee id: {employee_id}"
            }

        try:
            self.user_db.add_user(user_id, employee_id)
        except KeyError:
            return {"text": "You are already enrolled!"}

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
        return {"blocks": blocks}
