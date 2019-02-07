FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7-alpine3.8

RUN pip install pipenv

RUN apk add --no-cache postgresql-client postgresql-dev gcc libc-dev g++ make && \
    apk --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --no-cache add leveldb leveldb-dev

COPY . /app

WORKDIR /app

RUN pipenv lock --requirements > requirements.txt && pip install -r requirements.txt

RUN rm main.py ; ln -s api.py main.py
