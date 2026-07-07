# Running a Dagster+ Hybrid agent on Podman instead of Docker

This example covers two places where Docker gets swapped for Podman in a
Dagster+ **Hybrid** deployment:

1. **CI/CD** — building and pushing the code location image.
   See [`dagster-plus-hybrid-podman-deploy.yml`](./dagster-plus-hybrid-podman-deploy.yml).
2. **The agent runtime** — the Dagster+ Docker agent launching code servers
   and run containers. That's what this doc explains.

Podman is a daemonless, rootless-capable, drop-in replacement for Docker. The
Dagster+ Docker agent talks to a Docker-compatible API socket, and Podman
exposes exactly that socket — so the agent doesn't need to know it's not
Docker. You point it at Podman's socket and everything else is unchanged.

## 1. Enable the Podman API socket

Podman can serve the Docker-compatible REST API over a Unix socket.

**Rootful (recommended for a shared agent host):**

```bash
sudo systemctl enable --now podman.socket
# Socket: /run/podman/podman.sock
```

**Rootless (per-user):**

```bash
systemctl --user enable --now podman.socket
loginctl enable-linger "$USER"   # keep the socket alive after logout
# Socket: /run/user/$(id -u)/podman/podman.sock
```

Verify the socket answers the Docker API:

```bash
DOCKER_HOST=unix:///run/podman/podman.sock docker version   # if docker CLI installed
# or
curl -s --unix-socket /run/podman/podman.sock http://d/v1.41/version
```

## 2. Point the agent at the Podman socket

The Dagster+ Docker agent uses the standard `DOCKER_HOST` environment variable.
Set it to the Podman socket wherever the agent runs.

If you run the agent process directly:

```bash
export DOCKER_HOST=unix:///run/podman/podman.sock
dagster-cloud agent run
```

If you run the agent itself as a container (via `podman run` / a compose file),
mount the Podman socket in and set `DOCKER_HOST`:

```bash
podman run -d --name dagster-agent \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  -e DOCKER_HOST=unix:///run/podman/podman.sock \
  -e DAGSTER_CLOUD_AGENT_TOKEN=<agent-token> \
  -v /path/to/dagster.yaml:/opt/dagster/app/dagster.yaml \
  docker.io/dagster/dagster-cloud-agent:latest \
  dagster-cloud agent run /opt/dagster/app
```

## 3. Agent configuration (`dagster.yaml`)

The Docker agent config is unchanged from a Docker setup — the runtime
difference is entirely in the socket `DOCKER_HOST` points at:

```yaml
# dagster.yaml
instance_class:
  module: dagster_cloud.instance
  class: DagsterCloudAgentInstance

dagster_cloud_api:
  agent_token:
    env: DAGSTER_CLOUD_AGENT_TOKEN
  deployment: prod

user_code_launcher:
  module: dagster_cloud.workspace.docker
  class: DockerUserCodeLauncher
  config:
    networks:
      - dagster_cloud_agent
    # Any env vars / registry creds the launched containers need.
```

## Notes and gotchas

- **Image format:** build images with `podman build --format docker` (as the CI
  workflow does) so registries and the agent get a Docker v2 schema image.
- **Rootless networking:** rootless Podman uses `pasta`/`slirp4netns`. If code
  servers can't reach the agent or each other, prefer the rootful socket or a
  shared Podman network.
- **`container_context.yaml`:** per–code-location Docker runtime settings
  (networks, env vars, registry) still apply — the agent forwards them to
  Podman through the Docker-compatible API.
- **`podman-docker` shim:** installing the `podman-docker` package provides a
  `docker` command that calls Podman, useful for scripts/tools that hardcode
  `docker`.
