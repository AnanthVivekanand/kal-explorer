FROM python:3.7.2-slim-stretch

RUN set -ex ; \
    apt-get update ; \
    apt-get install libssl1.0-dev libsecp256k1-dev -y ; \
    rm -rf /var/lib/apt/lists/*

RUN set -ex ; \
    pip install pipenv

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --python 3

CMD ["/usr/local/bin/pipenv", "run", "python", "sync.py"]
