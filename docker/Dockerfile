FROM ubuntu:latest
RUN apt update \
    && apt -y upgrade \
    && apt -y install python3 curl python3.10-venv \
    && apt -y autoremove \
    && groupadd -g 1001 bsampson \
    && useradd -rm -d /home/bsampson -s /bin/bash -g bsampson -G sudo -u 1001 bsampson \
    && mkdir /home/bsampson/application /home/bsampson/.aws && chown -Rv 1001:1001 /home/bsampson/
USER bsampson
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY --chown=1001:1001 *.py *.toml /home/bsampson/application/
RUN cd /home/bsampson/application/ \
    && python3 -m venv venv \
    &&  . venv/bin/activate \
    && $HOME/.local/bin/poetry install \
    && deactivate


WORKDIR /home/bsampson/application
CMD . venv/bin/activate && /bin/bash



