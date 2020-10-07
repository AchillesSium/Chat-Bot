# Conversational-bot


## Development setup

### Setting up pre-commit hooks

Instructions, installation options and more information can be found on the
[pre-commit](https://pre-commit.com) tool's website. There is also a page for
[supported hooks](https://pre-commit.com/hooks) for more pre made hooks.

For information about git hooks, check the
[documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) or
the sample hooks in `.git/hooks` directory.

*TL;DR*
- install `pre-commit` tool (e.g `pip install pre-commit`)
- the `.pre-commit-config.yaml` is already in the git root directory
- run `pre-commit install` to setup the hooks on the repository
- optionally run `pre-commit run -a` to *manually* run the installed hooks on all the files
- the hooks will run automatically before any commit

### Setting up virtual environment

- Make sure you have python version 3.8
```bash
$ python3 --version
Python 3.8.5
```
- Install a virtual environment and activate it on **bash**, for other shells
  select the corresponding venv/bin/activate.\* script.
```bash
$ python3 -m venv venv
$ source venv/bin/activate
```
- Install the requirements
```bash
$ pip install -r requirements.txt
```

### Setting up the app locally for testing

- Create a slack workspace where you can install the app
- Create a new slack app [here](https://api.slack.com/apps), and follow the
  instructions
- Add needed scopes for the app from OAuth & Permissions. I have added the
  following scopes as of writing this.
  - `app_mentions:read`
  - `channels:history`
  - `chat:write`
  - `commands`
  - `im:history`
  - `incoming-webhooks`
- Install the app to the workspace from the *Install App* tab
- Copy the necessary tokens to `.env` file
  - copy the `.env.sample` file to `.env`
  - replace the dummy tokens with the actual ones: Signing secret from the
    *Basic Information*, and api token from *Install App* tab
  - Make sure the file is **not** added to git
- Install [ngrok](https://ngrok.com/download)

The following will need to be done for each testing session, i.e. when ever
you restart ngrok.

- Activate the virtual environment
- Start the bot application `python -m bot.app`
- Check the port the app is listening (should be 3000) and start a tunnel with
  `ngrok http <PORT_NUMBER>`
- Copy the **https** address printed out by ngrok and return to slack app
  settings.
- Add the following urls where `<NGROK>` is the address you just copied.
  - `<NGROK>/slack/events/interact` for *Interactivity & Shortcuts*
  - `<NGROK>/slack/events` for *Event Subscriptions*
  - `<NGROK>/slack/commands` for *Slash commands*

Now the app should be ready for testing in slack. All that is left to do is
edit, restart the app and repeat. **Do not** close the ngrok tunnel while
iterating on the app, otherwise the url changes.

Ps. The inconvenience with the random ngrok urls can be avoided with paid plan
and `--subdomain` switch to ngrok.
