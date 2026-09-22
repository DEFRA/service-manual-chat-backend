# service-manual-chat-backend

Answers questions about the Defra AI digital toolkit for the
[service-manual-ui](https://github.com/DEFRA/service-manual-ui) Ask the
toolkit page. `POST /ask` takes a question and returns an answer with its
sources and, where a rule applies, the rule quoted word for word.

This is work-in-progress. See [To Do List](./TODO.md)

## Try Ask the toolkit locally

Runs the toolkit site and this backend together on your laptop, answering
from real models in the Bedrock sandbox. About ten minutes the first time,
most of it image builds. No Python or Node needed on the host.

### You need

- Docker Desktop, running.
- Git access to this repo and to
  [DEFRA/service-manual-ui](https://github.com/DEFRA/service-manual-ui).
- Your own Bedrock sandbox API key. Ask Joel if you do not have one.

### Set up

1. Clone both repos side by side, so `../service-manual-ui` exists next to
   this checkout:

   ```bash
   git clone git@github.com:DEFRA/service-manual-chat-backend.git
   git clone git@github.com:DEFRA/service-manual-ui.git
   cd service-manual-chat-backend
   ```

2. Create `compose/secrets.env` from the example and paste your key in:

   ```bash
   cp compose/secrets.env.example compose/secrets.env
   ```

   The file is gitignored. Nothing else needs a personal value.

3. Start everything:

   ```bash
   ASK_ENGINE=bedrock docker compose --profile service up --build
   ```

4. Open <http://localhost:3000/ai-toolkit/ask> and ask a question. An answer
   takes about five seconds.

Leave out `ASK_ENGINE=bedrock` to get canned answers with no key at all.
`Ctrl+C` stops it; `docker compose --profile service down` removes the
containers.

### What to edit

- **The prompt**, `prompts/system.md`. Mounted into the container, so the
  next question uses your edit. No restart.
- **The pages**, `../service-manual-ui/src/server/ai-ask/*.njk` and the
  partials under `src/server/common/templates/partials/ask-*.njk`. Mounted,
  so refresh the browser. Styles in `src/client/stylesheets` need
  `docker compose exec frontend npm run build:frontend`.
- **The backend**, `app/`. Synced into the container by
  `docker compose --profile service up --watch`, and uvicorn reloads.
- **The model**. Set `BEDROCK_MODEL_ID` to any London model id the sandbox
  has, for example
  `BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0 ASK_ENGINE=bedrock docker compose --profile service up`.
  Claude 3 Haiku refuses prompt caching, so the backend turns it off for
  that model and every question pays full price.

### What a question costs

The whole toolkit goes to the model as instructions, about 26,000 tokens,
with a Bedrock cache point after it. The cache lives for 5 minutes and a
cached read costs a tenth of a fresh token, so a warm question on Claude
Sonnet 4.6 is about 1p and a cold one about 8p. Every answer logs
`input_tokens`, `output_tokens`, `cache_read_tokens` and
`cache_write_tokens`. Two questions inside 5 minutes should show
`cache_read_tokens` above 20,000 on the second. Nothing that changes per
request may go into the instructions: the cache key is the exact text.

### Settings

All read from the environment by `app/config.py`. Compose sets the ones
marked so; the rest are optional.

| Variable | Default | What it does |
| :-- | :-- | :-- |
| `ASK_ENGINE` | `stub` | `stub` answers from canned fixtures with no key. `bedrock` calls Amazon Bedrock. |
| `AWS_BEARER_TOKEN_BEDROCK` | none | Your sandbox API key, in `compose/secrets.env`. Read by boto3 directly. Not needed on CDP, where the task role signs requests. |
| `BEDROCK_MODEL_ID` | `anthropic.claude-sonnet-4-6` | Plain model id locally; an inference profile id or ARN on CDP. |
| `BEDROCK_REGION` | `eu-west-2` | London. No cross-region inference. |
| `BEDROCK_GUARDRAIL_ID`, `BEDROCK_GUARDRAIL_VERSION` | none | Empty locally. On CDP the platform gives one guardrail per profile. |
| `CONTENT_DIR` | `content` | The toolkit markdown pages the model answers from. Compose mounts `../service-manual-ui/src/content` here (override the host path with `CONTENT_DIR=... docker compose ...`). |
| `SYSTEM_PROMPT_PATH` | `prompts/system.md` | The prompt. Compose mounts `./prompts`. |
| `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` | set by compose | Points Bedrock at real AWS while `AWS_ENDPOINT_URL` sends everything else to localstack. Needed wherever both are set. |
| `FRONTEND_DIR` | `../service-manual-ui` | Compose only: where the site checkout is. |

### If it does not work

- **`Internal Server Error` from `/ask` and `KeyError: 'output'` in the
  logs.** The Bedrock call went to localstack. Check
  `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` is set (compose sets it; the dev
  script sets it too).
- **`UnrecognizedClientException` or `403` from Bedrock.** The key is
  missing, mistyped or expired. Check `compose/secrets.env` has one line,
  no quotes, no spaces, then `docker compose --profile service up` again so
  the container re-reads it.
- **`ValidationException` naming the model.** That model id is not enabled
  in the sandbox. Try the default.
- **`403` saying "your request did not allow prompt caching".** That model
  refuses cache points. Add it to `MODELS_WITHOUT_PROMPT_CACHING` in
  `app/ask/bedrock.py`.
- **`cache_read_tokens=0` on every question.** Either more than 5 minutes
  passed between questions, or something in the prompt or pages changed
  between them. Check the instructions are identical call to call.
- **The site answers instantly with the same few canned answers.** Either
  `ASK_ENGINE` was not set, or `service-manual-ui` is on a branch older
  than the `AI_TOOLKIT_ASK_API_URL` change.
- **Port 3000 or 8085 already in use.** Stop whatever holds it; the site
  must be on 3000 for its links to work.
- **Startup fails on Mongo.** The template pings Mongo at boot even though
  `/ask` never uses it. Run through compose, which starts Mongo, rather than
  `python -m app.main` alone.

The sandbox has no guardrails. Local use only, toolkit content only, and
never paste real correspondence in.

- [service-manual-chat-backend](#service-manual-chat-backend)
  - [Requirements](#requirements)
    - [Python](#python)
    - [Linting and Formatting](#linting-and-formatting)
    - [Docker](#docker)
  - [Local development](#local-development)
    - [Setup & Configuration](#setup--configuration)
    - [Development](#development)
    - [Testing](#testing)
    - [Production Mode](#production-mode)
  - [API endpoints](#api-endpoints)
  - [Custom Cloudwatch Metrics](#custom-cloudwatch-metrics)
  - [Pipelines](#pipelines)
    - [Dependabot](#dependabot)
    - [SonarCloud](#sonarcloud)
  - [Licence](#licence)
    - [About the licence](#about-the-licence)

## Requirements

### Python

Please install python `>= 3.12` and `pipx` in your environment. This template uses [uv](https://github.com/astral-sh/uv) to manage the environment and dependencies.

```python
# install uv via pipx
pipx install uv

# sync dependencies
uv sync

# source python venv
source .venv/bin/activate

# install the pre-commit hooks
pre-commit install
```

This opinionated template uses the [`Fast API`](https://fastapi.tiangolo.com/) Python API framework.

### Environment Variable Configuration

The application uses Pydantic's `BaseSettings` for configuration management in `app/config.py`, automatically mapping environment variables to configuration fields.

In CDP, environment variables and secrets need to be set using CDP conventions.  See links below:
- [CDP App Config](https://github.com/DEFRA/cdp-documentation/blob/main/how-to/config.md)
- [CDP Secrets](https://github.com/DEFRA/cdp-documentation/blob/main/how-to/secrets.md)

For local development - see [instructions below](#local-development).

### Linting and Formatting

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting Python code.

#### Running Ruff

To run Ruff from the command line:

```bash
# Run linting with auto-fix
uv run ruff check . --fix

# Run formatting
uv run ruff format .
```

#### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run linting and formatting checks automatically before each commit.

The pre-commit configuration is defined in `.pre-commit-config.yaml`

To set up pre-commit hooks:

```bash
# Set up the git hooks
pre-commit install
```

To run the hooks manually on all files:

```bash
pre-commit run --all-files
```

#### VS Code Configuration

For the best development experience, configure VS Code to use Ruff:

1. Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for VS Code
2. Configure your VS Code settings (`.vscode/settings.json`):

```json
{
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit"
    },
    "ruff.lint.run": "onSave",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    }
}
```

This configuration will:

- Format your code with Ruff when you save a file
- Fix linting issues automatically when possible
- Organize imports according to isort rules

#### Ruff Configuration

Ruff is configured in the `.ruff.toml` file

### Docker

This repository uses Docker throughput its lifecycle i.e. both for local development and the environments. A benefit of this is that environment variables & secrets are managed consistently throughout the lifecycle

See the `Dockerfile` and `compose.yml` for details

## Local development

### Setup & Configuration

Follow the convention below for environment variables and secrets in local development.

**Note** that it does not use `.env` or `python-dotenv` as this is not the convention in the CDP environment.

**Environment variables:** `compose/aws.env`.

**Secrets:** `compose/secrets.env`. You need to create this, as it's excluded from version control.

**Libraries:** Ensure the python virtual environment is configured and libraries are installed using `uv sync`, [as above](#python)

**Pre-Commit Hooks:** Ensure you install the pre-commit hooks, as above

### Development

This app can be run locally by either using the Docker Compose project or via the provided script `scripts/start_dev_server.sh`.

#### Using Docker Compose

To run the application using Docker Compose, you can use the following command:

```bash
docker compose --profile service up --build
```

If you want to enable hot-reloading, you can press the `w` key once the compose project is running to enable `watch` mode.

#### Using the provided script

To run the application using the provided script, you can execute:

```bash
./scripts/start_dev_server.sh
```

This script will:

- Check if Docker is running
- Start dependent services with Docker Compose (Localstack, MongoDB)
- Set up environment variables for local development
- Load configuration from compose/aws.env and compose/secrets.env
- Verify the Python virtual environment is set up
- Start the FastAPI application with hot-reload enabled

The service will then run on `http://localhost:8085`

### Testing

Ensure the python virtual environment is configured and libraries are installed using `uv sync`, [as above](#python)

Testing follows the [FastApi documented approach](https://fastapi.tiangolo.com/tutorial/testing/); using pytest & starlette.

To test the application run:

```bash
uv run pytest
```

## API endpoints

| Endpoint             | Description                    |
| :------------------- | :----------------------------- |
| `GET: /docs`         | Automatic API Swagger docs     |
| `GET: /health`       | Health check endpoint          |
| `GET: /example/test` | Simple example endpoint        |
| `GET: /example/db`   | Database query example         |
| `GET: /example/http` | HTTP client example            |
| `POST: /ask`         | Answer a toolkit question      |

`POST /ask` takes:

```json
{ "question": "Can I paste personal data into Copilot?", "previous_question": null, "conversation_id": null }
```

`question` is 1 to 500 characters. `previous_question` lets a follow-up
("what about research data?") be read against what came before. It returns
the shape `service-manual-ui` maps in `src/server/ai-ask/answer.js`:

```json
{
  "status": "answered",
  "message": "Plain English explanation, two to four sentences.",
  "rule_verbatim": {
    "text": "The rule, copied word for word from the page it cites.",
    "source": { "title": "Keeping data safe", "url": "/ai-toolkit/guidance/keeping-data-safe", "section": "Remove personal data from anything you put in" }
  },
  "sources": [
    { "title": "Keeping data safe", "url": "/ai-toolkit/guidance/keeping-data-safe", "section": null }
  ]
}
```

`rule_verbatim` is `null` when no rule applies, and is dropped by the
backend if the quoted words are not on the cited page, or are only part of a
sentence there (`app/ask/quote_check.py`). `sources` only ever names pages in
`CONTENT_DIR`.

`status` is one of six outcomes. `message` is always present; the other
fields depend on the status.

| Status | Means | Extra fields |
| :-- | :-- | :-- |
| `answered` | The pages answer the question. | `rule_verbatim`, `sources` |
| `need_more_detail` | Too broad. The reader picks a narrower question, or types one. | `options`, 2 to 4 short phrases |
| `cannot_answer` | No answer here. | `reason`: `outside_toolkit` or `no_guidance_yet` |
| `talk_to_a_person` | About the reader's own project; the team is the right place. | `sources` may point at the nearest page |
| `blocked` | Refused, in neutral words. | none |
| `error` | The backend got no answer. Try again. | none |

With `ASK_ENGINE=stub` each outcome has a trigger, so the screens can be
built without a model: "help me" (need more detail), "parking" (outside the
toolkit), "buying" (no guidance yet), "my project" (talk to a person),
"medical" (blocked), "simulate an error" (error).

## Custom Cloudwatch Metrics

Uses the [aws embedded metrics library](https://github.com/awslabs/aws-embedded-metrics-python). An example can be found in `metrics.py`

In order to make this library work in the environments, the environment variable `AWS_EMF_ENVIRONMENT=local` is set in the app config. This tells the library to use the local cloudwatch agent that has been configured in CDP, and uses the environment variables set up in CDP `AWS_EMF_AGENT_ENDPOINT`, `AWS_EMF_LOG_GROUP_NAME`, `AWS_EMF_LOG_STREAM_NAME`, `AWS_EMF_NAMESPACE`, `AWS_EMF_SERVICE_NAME`

## Pipelines

### Dependabot

We have added an example dependabot configuration file to the repository. You can enable it by renaming
the [.github/example.dependabot.yml](.github/example.dependabot.yml) to `.github/dependabot.yml`

### SonarCloud

Instructions for setting up SonarCloud can be found in [sonar-project.properties](./sonar-project.properties)

## Licence

THIS INFORMATION IS LICENSED UNDER THE CONDITIONS OF THE OPEN GOVERNMENT LICENCE found at:

<http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3>

The following attribution statement MUST be cited in your products and applications when using this information.

> Contains public sector information licensed under the Open Government license v3

### About the licence

The Open Government Licence (OGL) was developed by the Controller of Her Majesty's Stationery Office (HMSO) to enable
information providers in the public sector to license the use and re-use of their information under a common open
licence.

It is designed to encourage use and re-use of information freely and flexibly, with only a few conditions.
