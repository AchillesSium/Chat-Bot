from apscheduler.schedulers.background import BackgroundScheduler
from typing import NamedTuple, Optional, Callable, List

from datetime import datetime, timedelta

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

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._tick)
        self.scheduler.start()

    def help(self):
        return {
            "text": "Example help message:\nTo enrol, send me a message like: 'enrol <employee_id>'",
        }

    def _tick(self):
        print("tick", datetime.now())
        self._check_skill_recommendations()
        self.scheduler.add_job(self._tick, "date", run_date=self._next_tick())

    def _next_tick(self) -> datetime:
        # TODO: configure the interval
        date = datetime.now() + timedelta(seconds=30)
        return date

    def _check_skill_recommendations(self):
        now = datetime.now()
        # TODO: skip weekends and non working hours
        # TODO: configure the interval for skill suggestions
        limit = timedelta(seconds=20)
        users = self.user_db.get_users()
        for user_id, employee_id in users:
            history = self.user_db.get_history_by_user_id(user_id)
            if history:
                last = history[0][1]
                if now - last < limit:
                    continue
            rec = self._recommendations_for(employee_id=employee_id, history=history)
            if not rec:
                continue
            _ = self.send_message(user_id, self._format_skill_recommendations(rec))
            # if ok:
            #     for skill in rec:
            #         self.user_db.add_history(user_id, now, skill)

    def _recommendations_for(
        self, *, user_id=None, employee_id=None, history=None, limit=2
    ):
        assert (user_id is None) ^ (
            employee_id is None
        ), "exactly one of the id's must be provided"
        if employee_id is None:
            _, employee_id = self.user_db.get_user_by_id(user_id)
        try:
            rec = self.recommender.recommend_skills_to_user(employee_id)
        except KeyError:
            return []
        skills = rec.recommendation_list
        if history is None:
            history = self.user_db.get_history_by_user_id(user_id)
        if not history:
            return skills[:limit]
        previous = {item for _id, _date, item in history}
        return [item for item in skills if item not in previous][:limit]

    def _format_skill_recommendations(self, recommendation_list):
        if recommendation_list:
            text = "Based on you profile, we found some skills that you might also have, but which are not listed on your profile.\n"
        else:
            text = "We found no skills to suggest this time"

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": text},}]

        if recommendation_list:
            checklist_options = [
                {"text": {"type": "mrkdwn", "text": f"*{rec}*"}, "value": rec}
                for rec in recommendation_list
            ]

            blocks.extend(
                [
                    {
                        "type": "section",
                        "block_id": "skill_suggestions",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please select the skills you *do not* want to see in your suggestions anymore",
                        },
                        "accessory": {
                            "type": "checkboxes",
                            "options": checklist_options,
                            "action_id": "checked_suggestions",
                        },
                    },
                    {
                        "type": "actions",
                        "block_id": "skill_suggestion_button",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Send"},
                                "style": "primary",
                                "value": "reply_to_suggestions",
                                "action_id": "skill_suggestion_reply",
                            }
                        ],
                    },
                ]
            )

        return {"blocks": blocks}

    def update_user_history(self, user_id: str, skills: List[str]):
        now = datetime.now()

        for skill in skills:
            self.user_db.add_history(user_id, now, skill)

        if len(skills) > 1:
            skill_str = "s " + ", ".join(skills[:-1]) + f" or {skills[-1]}"
        elif len(skills) == 1:
            skill_str = " " + skills[0]
        else:
            return {
                "text": "You did not select any skills from the list. Please select the skills that you do not want to "
                "see in your suggestions anymore."
            }

        return {
            "text": f"Thank you for your input! We will no longer suggest the skill{skill_str} to you."
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

        rec = self._recommendations_for(employee_id=employee_id, limit=None)
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Success!* You are now enrolled"},
            },
            *self._format_skill_recommendations(rec)["blocks"],
        ]

        return {"blocks": blocks}
