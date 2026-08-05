ARG PANDOC_VERSION=3.10.1

FROM python:3.14-slim AS build

WORKDIR /src
COPY . .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir .

ARG PANDOC_VERSION
ARG TARGETARCH
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && curl -fsSL -o /opt/pandoc.deb \
      "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-${TARGETARCH}.deb"

FROM python:3.14-slim

COPY --from=build /opt/pandoc.deb /tmp/pandoc.deb
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates /tmp/pandoc.deb \
 && rm -rf /tmp/pandoc.deb /var/lib/apt/lists/*

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["migrate-rg"]
CMD ["--help"]
