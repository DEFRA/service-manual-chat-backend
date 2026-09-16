# To Do
Once "hello world" is deployed and running in dev:

1. A python base image (including the self-signed cert)
   Partially done, certs are loaded via environment variables, the same way we handle them in node.
3. Other Github actions - `publish-hotfix.yml`, `example.dependabot.yml`
4. Sonar config - `sonar-project.properties`
5. At the moment, the argument `--no-access-log` is provided in the `Dockerfile`, [as per docs](https://www.uvicorn.org/settings/#logging). A more fine-grained approach to just prevent logging access to `/health` can be implemented, [as per this](https://github.com/encode/starlette/issues/864)
