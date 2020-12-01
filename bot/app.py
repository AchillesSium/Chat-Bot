from flask import Flask, Response, request, make_response

from slack import WebClient
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier
from slackeventsapi import SlackEventAdapter

import atexit
import json
import os

from dotenv import load_dotenv, find_dotenv

from bot.bot import Bot
from bot.chatBotDatabase import get_database_object

# Get the tokens from .env file (.env.sample in version control)
# Use load_dotenv to enable overwriting the values from system environment
# variables, or from commandline
load_dotenv(find_dotenv())
ENV = os.environ
SLACK_SIGNING_SECRET = ENV["SLACK_SIGNING_SECRET"]
SLACK_API_TOKEN = ENV["SLACK_API_TOKEN"]

app = Flask(__name__)

# instantiating slack client
slack_client = WebClient(SLACK_API_TOKEN)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)


def send_message(user_id, message):
    """Send direct message to the user from the bot.

    :param user_id: Slack user id
    :param message: message as dictionary

    :return: True if sending succeeds
    """
    response = slack_client.api_call(
        api_method="conversations.open", json={"users": user_id}
    )
    try:
        response.validate()
        channel_id = response["channel"]["id"]
        result = slack_client.chat_postMessage(channel=channel_id, **message)
        result.validate()
    except SlackApiError as e:
        print(repr(e))
        return False
    return True


CRON = ENV["BOT_CHECK_SCHEDULE"]
INTERVAL = int(ENV["BOT_DAYS_BETWEEN_MESSAGES"])

DB_TYPE = ENV["DB_TYPE"]
DB_CONNECTION_STRING = ENV["DB_CONNECTION_STRING"]

bot_db = get_database_object(DB_TYPE, DB_CONNECTION_STRING, retry_delays=(1, 2, 5))
atexit.register(bot_db.close)

bot = Bot(
    send_message=send_message,
    check_schedule=CRON,
    message_interval=INTERVAL,
    user_db=bot_db,
)


@app.route("/slack/events/interact", methods=["POST"])
def interaction():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)

    print(request.form)
    json_form = json.loads(request.form.get("payload"))
    user_id = json_form["user"]["id"]
    action_dict = json_form["actions"][0]

    def get_selected_skills():
        sep = "___"
        result = set()
        try:
            selected_options = json_form["state"]["values"]["skill_suggestions"][
                "checked_suggestions"
            ]["selected_options"]
            result.update(
                selected_option["value"].split(sep)[0]
                for selected_option in selected_options
            )
        except KeyError:
            result = []

        for block in json_form["message"]["blocks"]:
            if block["block_id"] == "skill_suggestions":
                acc = block["accessory"]
                init_opts = acc.get("initial_options")

                if init_opts is not None:
                    for i in init_opts:
                        result.add(i["value"].split(sep)[0])

        return list(result)

    if action_dict["action_id"] == "skill_suggestion_reply":
        # This is fired when the user pushes the "Send" button
        selected_skills = get_selected_skills()

        slack_client.chat_postMessage(
            channel=user_id, **bot.update_user_history(user_id, selected_skills)
        )

        return make_response("", 200)

    elif action_dict["action_id"] == "checked_suggestions":
        # This is fired when the user is checking the checkboxes
        return make_response("", 200)

    elif action_dict["action_id"] == "show_more_suggestions":
        og_timestamp = json_form["container"]["message_ts"]
        channel = json_form["channel"]["id"]
        nb_already_suggested, message_id = action_dict["value"].split("___")
        nb_already_suggested = int(nb_already_suggested)

        selected_skills = get_selected_skills()
        formatted_suggestions = bot.show_more_skills(
            user_id,
            nb_already_suggested,
            already_selected=selected_skills,
            message_id=message_id,
        )

        slack_client.chat_update(
            channel=channel, ts=og_timestamp, **formatted_suggestions
        )

    elif action_dict["action_id"] == "show_more_candidates":
        og_timestamp = json_form["container"]["message_ts"]
        channel = json_form["channel"]["id"]
        nb_already_suggested, query_skills, query_year, query_week = action_dict[
            "value"
        ].split("_")
        nb_already_suggested = int(nb_already_suggested)
        query_skills = query_skills.split(",")
        query_year = int(query_year)
        query_week = int(query_week)

        formatted_suggestions = bot.show_more_candidates(
            (query_skills, query_year, query_week), nb_already_suggested
        )

        slack_client.chat_update(
            channel=channel, ts=og_timestamp, **formatted_suggestions
        )

    return make_response("", 404)


@app.route("/slack/commands", methods=["POST"])
def slash_commands():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)
    print(request.form)
    if command := request.form.get("command"):
        user_id = request.form["user_id"]
        return {
            **bot.reply(user_id, command + " " + request.form["text"]),
            "response_type": "ephemeral",
        }
    return make_response("", 404)


@slack_events_adapter.on("message")
def handle_direct_message(event_data):
    print("message", event_data)
    message = event_data["event"]
    if (
        not message.get("bot_id")  # don't reply to bot's own messages
        and message.get("subtype") is None
        and message.get("channel_type") == "im"
    ):
        command = message.get("text")
        user = message["user"]
        channel = message["channel"]
        response = bot.reply(user, command)
        slack_client.chat_postMessage(channel=channel, user=user, **response)
    return Response(status=200)


@slack_events_adapter.on("app_mention")
def handle_message(event_data):
    print("mention", event_data)
    message = event_data["event"]
    if message.get("subtype") is None:
        command = message.get("text")
        channel_id = message["channel"]
        ts = message["ts"]
        user = message["user"]
        message = f"Hi <@{user}>! :tada:"
        slack_client.chat_postMessage(channel=channel_id, text=message)
    return Response(status=200)


# Start the server on port 3000
if __name__ == "__main__":
    app.run(port=3000)
