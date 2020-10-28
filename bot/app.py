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
        not message.get("bot_id")
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
