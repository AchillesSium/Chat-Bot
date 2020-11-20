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
#### Optional (for now at least):
- Download nltk packages for language processing
```bash
$  python3 -c "import nltk;nltk.download('punkt');nltk.download('averaged_perceptron_tagger');nltk.download('stopwords')"
```

### Setting up the app locally for testing

- Create a slack workspace where you can install the app
- Create a new slack app [here](https://api.slack.com/apps), and follow the
  instructions
- Add needed scopes for the app from the *OAuth & Permissions* tab in the sidebar under **Features**.
  Add the scopes in the **Scopes** -> **Bot token scopes** section. I have added the
  following scopes as of writing this.
  - `app_mentions:read`
  - `channels:history`
  - `chat:write`
  - `commands`
  - `im:history`
  - `incoming-webhook`
- Add the needed event subscriptions from the *Event Subscriptions* tab in the sidebar under **Features**.
  Add the subscriptions in the **Subscribe to bot events** section. Needed events are the following:
  - `app_mention`
  - `message.channels`
  - `message.im`
- Install the app to the workspace from the *Install App* tab under **Settings**
- Copy the necessary tokens to `.env` file
  - copy the `.env.sample` file to `.env`
  - replace the dummy tokens with the actual ones: Signing secret from the
    *Basic Information*, and api token from *Install App* tab
  - Make sure the file is **not** added to git
- Install [ngrok](https://ngrok.com/download)

For now, you also need to download the json-formatted sample data files `people-simple.json` and `allocation.json`
to the parent directory of your repository.

The following will need to be done for each testing session, i.e. when ever
you restart ngrok.

- Activate the virtual environment
- To configure the automatic checks, use the environment variables
  `BOT_CHECK_SCHEDULE` and `BOT_DAYS_BETWEEN_MESSAGES`. The
  shortest interval (once a minute) can be achieved by setting:
  - `export BOT_CHECK_SCHEDULE="* * * * *"`
  - `export BOT_DAYS_BETWEEN_MESSAGES=0`
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

### Setting up Docker

Download [Docker desktop](https://www.docker.com/products/docker-desktop).

Make sure docker desktop is running when you want to run docker on you machine.

Now go through the following commands:

- On the terminal, build the docker image with the command as follow:
```bash
$ docker-compose build
```
- On the terminal, run the docker with the command as follow:
```bash
$ docker-compose up
```
- To turn down docker run the command as follow:
```bash
$ docker-compose down
```
