FROM gitlab/gitlab-ce:latest

ENV PANDOC_BIN=https://github.com/jgm/pandoc/releases/download/2.10.1/pandoc-2.10.1-1-amd64.deb

RUN apt-get update && apt-get install -y \
    sudo
RUN wget -q ${PANDOC_BIN} && \
    dpkg -i `basename ${PANDOC_BIN}` && \
    rm -f `basename ${PANDOC_BIN}`

COPY . /opt/redmine-gitlab-migrator
RUN cd /opt/redmine-gitlab-migrator && \
    python3 -m venv venv && \
    . venv/bin/activate && \
    python setup.py install && \
    echo "#!/bin/sh\n. /opt/redmine-gitlab-migrator/venv/bin/activate\nmigrate-rg \$@" \
    > /usr/local/bin/migrate-rg && \
    chmod +x /usr/local/bin/migrate-rg
