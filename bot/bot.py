from apscheduler.schedulers.background import BackgroundScheduler
from typing import NamedTuple, Optional, Callable, List, Iterable

import re
from datetime import datetime, timedelta

from bot.data_api.datasource import Datasource
from bot.recommenders.skill_recommender import SkillRecommendation, SkillRecommenderCF
from bot.chatBotDatabase import BotDatabase


class User(NamedTuple):
    id: str
    employee_id: int


class Command(NamedTuple):
    name: str
    match: Callable[[str], Optional[re.Match]]
    action: Callable[[str, str, re.Match], dict]
    requires_enrollment: bool = True
    help_text: str = ""

    @property
    def help(self):
        text = f"`{self.name}`"
        if self.help_text:
            text += "  " + self.help_text
        if self.requires_enrollment:
            text += "  (enrollment required)"
        return text


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

        def matcher(regex):
            return re.compile(regex, re.IGNORECASE).match

        self._commands = [
            Command(
                "enrol",
                matcher(r"(?:\<@\S+\>\s+|/)?enrol+\s+(?P<id>\d+)"),
                self.enrol_user,
                requires_enrollment=False,
                help_text="usage: `enrol <employee_id>`",
            ),
            Command("skills", matcher("skills?"), self.skills_command,),
            Command(
                "sign-off",
                matcher("sign.?off"),
                self.sign_off,
                help_text="leave the service",
            ),
        ]

    def help(self):
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Hi!* I understand the following commands:",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "- `help` (this message)"},
                },
                *(
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "- " + command.help},
                    }
                    for command in self._commands
                ),
            ]
        }

    def reply(self, user_id: str, message: str):
        """
        Tries to match a command from the message, and replies accordingly.
        If the message is not recognised, reply with help message.
        """
        enrolled = self._is_enrolled(user_id)
        for command in self._commands:
            if match := command.match(message):
                if command.requires_enrollment and not enrolled:
                    # TODO: maybe ask the user to enrol?
                    break
                return command.action(user_id, message, match)
        return self.help()

    def skills_command(self, user_id: str, _message: str, _match):
        rec = self._recommendations_for(user_id=user_id, limit=None)
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Hi!* Thanks for asking"},
                },
                *self._format_skill_recommendations(rec)["blocks"],
            ]
        }

    def sign_off(self, user_id: str, _message: str, _match):
        self.user_db.delete_user(user_id)
        return {
            "text": "Success! You are now signed-off!\nYou can come back at any time by enrolling.",
        }

    def _is_enrolled(self, user_id: str) -> bool:
        try:
            self.user_db.get_user_by_id(user_id)
        except KeyError:
            return False
        return True

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
            ok = self.send_message(user_id, self._format_skill_recommendations(rec))
            if ok:
                for skill in rec:
                    self.user_db.add_history(user_id, now, skill)

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
            skills = "\n".join(f"- {r}" for r in recommendation_list)
            text = "We found these skills similar to yours:\n" + skills
        else:
            text = "We found no skills to suggest this time"
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": text,},},
        ]
        return {"blocks": blocks}

    def enrol_user(self, user_id: str, _message, match: re.Match):
        employee_id = int(match.group("id"))
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
