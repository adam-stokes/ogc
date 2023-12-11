FROM python:3.11-slim-buster as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    lsb-release wget gpg gcc build-essential git software-properties-common openssh-client locales \
  && rm -rf /var/lib/apt/lists/*
RUN sed -i 's/^# *\(en_US.UTF-8\)/\1/' /etc/locale.gen
RUN locale-gen

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8

WORKDIR /code

from base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive
RUN pip --no-cache-dir install wheel build
RUN python -m venv /venv

COPY requirements-dev.lock requirements.lock ./
RUN sed '/-e/d' requirements.lock > requirements.txt
RUN sed '/-e/d' requirements-dev.lock > requirements-dev.txt
RUN /venv/bin/pip install -r requirements.txt
RUN /venv/bin/pip install -r requirements-dev.txt

COPY . .
RUN python -m build && /venv/bin/pip install wheel && /venv/bin/pip install dist/*.whl

FROM base as final
COPY --from=builder /venv /venv

COPY dev.sh /
ENTRYPOINT ["/dev.sh"]
