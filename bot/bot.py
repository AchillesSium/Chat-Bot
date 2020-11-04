from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import NamedTuple, Optional, Callable, List, Iterable, Dict, Any, Tuple

import re
from datetime import datetime, timedelta

from bot.data_api.datasource import Datasource
from bot.recommenders.skill_recommender import SkillRecommendation, SkillRecommenderCF
from bot.chatBotDatabase import BotDatabase, User, HistoryEntry


BotReply = Dict[str, Any]


class Command(NamedTuple):
    name: str
    match: Callable[[str], Optional[re.Match]]
    action: Callable[[str, str, re.Match], BotReply]
    """
    Function responsible for the action associated with the command
    parameters:
      - user_id
      - message body
      - match object, from matching the message with command's match attribute
    returns: dictionary of elements for slack message, e.g.
      - {"text": <the message text>}
      - {"blocks": <list of block elements>}
    """
    requires_signup: bool = True
    help_text: str = ""

    @property
    def help(self):
        "Formatted help text for the command"
        text = f"`{self.name}`"
        if self.help_text:
            text += "  " + self.help_text
        if self.requires_signup:
            text += "  (signing up required)"
        return text


class Bot:
    def __init__(
        self,
        send_message: Callable[[str, dict], bool],
        check_schedule: str,
        message_interval: int,
        user_db: Optional[BotDatabase] = None,
        data_source: Optional[Datasource] = None,
    ):
        self.send_message = send_message
        self.user_db: BotDatabase = user_db or BotDatabase(":memory:")
        self.data_source: Datasource = data_source or Datasource()
        self.recommender = SkillRecommenderCF(self.data_source)

        self._message_interval = timedelta(days=message_interval)

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._tick, CronTrigger.from_crontab(check_schedule))
        self.scheduler.start()

        def matcher(regex):
            return re.compile(regex, re.IGNORECASE).match

        self._commands = [
            Command(
                "help",
                matcher("help"),
                self.help,
                requires_signup=False,
                help_text="(this message)",
            ),
            Command(
                "sign-up",
                # Matches
                #   optional mention or '/'  (this is not captured as a group)
                #   'sign' (optional character, e.g. '-' or ' ') 'up'
                #   one or more space
                #   one or more digits (captured in group called 'id')
                # The mention is received in the form: '<@' slack_id '>'
                # but the user types and sees: '@' slack_name
                # Examples
                #   <@ABCD123EFGH> sign-up 123
                #   /signup   4
                #   sign up 567
                matcher(r"(?:\<@\S+\>\s+|/)?sign.?up\s+(?P<id>\d+)"),
                self.sign_up,
                requires_signup=False,
                help_text="usage: `sign-up <employee_id>`",
            ),
            Command("skills", matcher("skills?"), self.skills_command,),
            Command(
                "sign-off",
                matcher("sign.?off"),
                self.sign_off,
                help_text="leave the service",
            ),
        ]

    def help(self, *_) -> BotReply:
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Hi!* I understand the following commands:",
                    },
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

    def reply(self, user_id: str, message: str) -> BotReply:
        """
        Tries to match a command from the message, and replies accordingly.
        If the message is not recognised, reply with help message.

        :param user_id: Slack user id
        :param message: message body

        :return: reply to message
        """
        signed_up = self._is_signed_up(user_id)
        for command in self._commands:
            if match := command.match(message):
                if command.requires_signup and not signed_up:
                    break
                return command.action(user_id, message, match)
        return self.find_candidates(message)

    def find_candidates(self, message):
        "Find candidate employees who have particular skills"

        skills = {s.strip() for s in message.split(",")}

        # TODO: find the actual free people with the skills
        people = [{"id": 123, "matching_skills": ("js", "angular")}]

        if not people:
            return {"text": "I could not find anyone available with those skills"}

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I found the following employees who are free next",
                },
            }
        ]

        for person in people[:5]:
            id_ = person["id"]
            skill = ", ".join(person["matching_skills"])
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{id_}* with skills: {skill}"},
                }
            )

        # TODO: add button to fetch more people, if available
        return {"blocks": blocks}

    def skills_command(self, user_id: str, _message: str, _match) -> BotReply:
        rec = self._recommendations_for(user_id=user_id, limit=None)
        self.user_db.set_next_reminder(user_id, datetime.now() + self._message_interval)
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Hi!* Thanks for asking"},
                },
                *self._format_skill_recommendations(rec)["blocks"],
            ]
        }

    def sign_off(self, user_id: str, _message: str, _match) -> BotReply:
        self.user_db.delete_user(user_id)
        return {
            "text": "Success! You are now signed-off!\nYou can come back at any time by signing up.",
        }

    def _is_signed_up(self, user_id: str) -> bool:
        try:
            self.user_db.get_user_by_id(user_id)
        except KeyError:
            return False
        return True

    def _tick(self):
        print("tick", datetime.now())
        self._check_skill_recommendations()

    def _check_skill_recommendations(self):
        now = datetime.now()
        for user in self.user_db.get_users():
            if user.remind_next and user.remind_next > now:
                continue
            rec = self._recommendations_for(employee_id=user.employee_id)
            if not rec:
                continue
            self.user_db.set_next_reminder(user.user_id, now + self._message_interval)
            self.send_message(user.user_id, self._format_skill_recommendations(rec))

    def _recommendations_for(
        self,
        *,
        user_id: str = None,
        employee_id: int = None,
        history: Iterable[HistoryEntry] = None,
        limit: Optional[int] = 5,
    ):
        """Return list of recommendations for user.

        Exactly one of user_id or employee_id must be given.

        The history is used to exclude those items from recommendations.
        When None, history is fetched from the database.

        :param user_id: Slack user id
        :param employee_id: Vincit employee id
        :param history: recommendations to exclude
        :param limit: maximum number of recommendations to return, use None for no limit

        :return: list of recommendations
        """
        assert (user_id is None) ^ (
            employee_id is None
        ), "exactly one of the id's must be provided"
        if employee_id is None:
            assert user_id is not None
            user = self.user_db.get_user_by_id(user_id)
            employee_id = user.employee_id
        try:
            rec = self.recommender.recommend_skills_to_user(employee_id)
        except KeyError:
            return []
        skills = rec.recommendation_list
        if history is None:
            if user_id is None:
                assert employee_id is not None
                [user] = self.user_db.get_user_by_employeeid(employee_id)
                user_id = user.user_id
            history = self.user_db.get_history_by_user_id(user_id)
        if not history:
            return skills[:limit]
        previous = {item for _id, _date, item in history}
        return [item for item in skills if item not in previous][:limit]

    def _format_skill_recommendations(self, recommendation_list) -> BotReply:
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

    def sign_up(self, user_id: str, _message, match: re.Match) -> BotReply:
        """Sign user up and return initial recommendations

        :param user_id: Slack user id
        :param match: match object containing the employee id

        :return: reply with recommendations or error message
        """
        employee_id = int(match.group("id"))
        if self.data_source.user_info(employee_id) is None:
            return {
                "text": f"Hmm... There is no record for the employee id: {employee_id}"
            }

        try:
            self.user_db.add_user(
                User(user_id, employee_id, datetime.now() + self._message_interval)
            )
        except KeyError:
            return {"text": "You are already signed-up!"}

        rec = self._recommendations_for(employee_id=employee_id)
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Success!* You are now signed-up"},
            },
            *self._format_skill_recommendations(rec)["blocks"],
        ]

        return {"blocks": blocks}
