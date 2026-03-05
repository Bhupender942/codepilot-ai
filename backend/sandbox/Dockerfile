FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest pytest-asyncio

RUN groupadd --gid 10001 sandbox && \
    useradd --uid 10001 --gid sandbox --no-create-home --shell /bin/false sandbox

WORKDIR /sandbox

RUN chown sandbox:sandbox /sandbox

USER sandbox

# The sandbox container is started per-run with a bind-mounted workspace;
# the actual command is supplied at container-run time.
CMD ["python", "-m", "pytest", "--tb=short", "-q"]
