from flask import Flask, Response, request, make_response

from slack import WebClient
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier
from slackeventsapi import SlackEventAdapter

import json
import re

from dotenv import dotenv_values, find_dotenv

from .bot import Bot

# Get the tokens from .env file (.env.sample in version control)
ENV = dotenv_values(find_dotenv())
SLACK_SIGNING_SECRET = ENV["SLACK_SIGNING_SECRET"]
SLACK_API_TOKEN = ENV["SLACK_API_TOKEN"]

app = Flask(__name__)

# instantiating slack client
slack_client = WebClient(SLACK_API_TOKEN)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)


def send_message(user_id, message):
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


bot = Bot(send_message=send_message)


@app.route("/slack/events/interact", methods=["POST"])
def interaction():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)

    print(request.form)
    json_form = json.loads(request.form.get("payload"))
    user_id = json_form["user"]["id"]
    action_dict = json_form["actions"][0]

    if action_dict["action_id"] == "skill_suggestion_reply":
        # This is fired when the user pushes the "Send" button
        try:
            selected_options = json_form["state"]["values"]["skill_suggestions"][
                "checked_suggestions"
            ]["selected_options"]
            selected_skills = [
                selected_option["value"] for selected_option in selected_options
            ]
        except KeyError:
            selected_skills = []

        slack_client.chat_postMessage(
            channel=user_id, **bot.update_user_history(user_id, selected_skills)
        )

        return make_response("", 200)

    elif action_dict["action_id"] == "checked_suggestions":
        # This is fired when the user is checking the checkboxes
        # TODO: I think it's possible to update messages. So maybe disable boxes when they're checked?
        return make_response("", 200)

    return make_response("", 404)


@app.route("/slack/commands", methods=["POST"])
def slash_commands():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)
    print(request.form)
    if request.form.get("command") == "/enrol":
        try:
            user_id = request.form["user_id"]
            employee_id = int(request.form["text"])
            return {
                **bot.enrol_user(user_id, employee_id),
                "response_type": "ephemeral",
            }
        except Exception as e:
            print(f"error: {e!r}")
            return {
                **bot.help(),
                "response_type": "ephemeral",
            }
    return make_response("", 404)


@slack_events_adapter.on("message")
def handle_direct_message(event_data):
    print("message", event_data)
    message = event_data["event"]
    if message.get("subtype") is None and message.get("channel_type") == "im":
        command = message.get("text")
        match = re.match(r"(?:\<@\S+\>\s+)?enrol+\s+(\d+)", command, re.IGNORECASE)
        user = message["user"]
        channel = message["channel"]
        if match:
            employee_id = int(match.group(1))
            response = bot.enrol_user(user, employee_id)
            slack_client.chat_postEphemeral(channel=channel, user=user, **response)
            return Response(status=200)
        response = bot.help()
        slack_client.chat_postEphemeral(channel=channel, user=user, **response)
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
