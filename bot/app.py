from flask import Flask, Response, request, make_response

from slack import WebClient
from slack.signature import SignatureVerifier
from slackeventsapi import SlackEventAdapter

import json

from dotenv import dotenv_values, find_dotenv

# Get the tokens from .env file (.env.sample in version control)
ENV = dotenv_values(find_dotenv())
SLACK_SIGNING_SECRET = ENV["SLACK_SIGNING_SECRET"]
SLACK_API_TOKEN = ENV["SLACK_API_TOKEN"]

app = Flask(__name__)

# instantiating slack client
slack_client = WebClient(SLACK_API_TOKEN)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)


@app.route("/slack/events/interact", methods=["POST"])
def slack_app():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)
    if "payload" in request.form:
        payload = json.loads(request.form["payload"])
        if (
            payload["type"] == "shortcut"
            and payload["callback_id"] == "open-modal-shortcut"
        ):
            # Open a new modal by a global shortcut
            try:
                api_response = slack_client.views_open(
                    trigger_id=payload["trigger_id"],
                    view={
                        "type": "modal",
                        "callback_id": "modal-id",
                        "title": {"type": "plain_text", "text": "Title goes here"},
                        "submit": {"type": "plain_text", "text": "Submit"},
                        "close": {"type": "plain_text", "text": "Cancel"},
                        "blocks": [
                            {
                                "type": "input",
                                "label": {
                                    "type": "plain_text",
                                    "text": "What the field is about",
                                },
                                "element": {
                                    "action_id": "a-id",
                                    "type": "plain_text_input",
                                },
                            },
                        ],
                    },
                )
                return make_response("", 200)
            except Exception as e:
                code = e.response["error"]
                return make_response(f"Failed to open a modal due to {code}", 200)
        if (
            payload["type"] == "view_submission"
            and payload["view"]["callback_id"] == "modal-id"
        ):
            # Handle a data submission request from the modal
            submitted_data = payload["view"]["state"]["values"]
            print(submitted_data)
            return make_response("", 200)
    return make_response("", 404)


@slack_events_adapter.on("app_mention")
def handle_message(event_data):
    print("event", event_data)
    message = event_data["event"]
    if message.get("subtype") is None:
        command = message.get("text")
        channel_id = message["channel"]
        ts = message["ts"]
        user = message["user"]
        message = f"Hi, <@{user}>! :tada:"
        slack_client.chat_postMessage(channel=channel_id, text=message)
    return Response(status=200)


# Start the server on port 3000
if __name__ == "__main__":
    app.run(port=3000)
