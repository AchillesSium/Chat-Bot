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
