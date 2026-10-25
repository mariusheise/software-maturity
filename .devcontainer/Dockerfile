FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential ca-certificates cmake gdb git jq ninja-build python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && git config --system --add safe.directory '*'

# Non-root user matching the default Ubuntu "ubuntu" account (uid 1000).
USER ubuntu
RUN conan profile detect --force
# Mount point of the Claude Code volume (devcontainer.json). Created here so the new volume is
# owned by ubuntu; with CLAUDE_CONFIG_DIR it keeps sessions, memory, settings and login across
# rebuilds.
RUN mkdir -p /home/ubuntu/.claude
