FROM python:3.7-alpine3.8

# LABEL maintainer="Ryan Shaw <ryan@rshaw.me>"

RUN apk add --no-cache curl \
 && curl -L -s https://github.com/just-containers/s6-overlay/releases/download/v1.18.1.5/s6-overlay-amd64.tar.gz \
  | tar xvzf - -C / \
 && apk del --no-cache curl

ENTRYPOINT [ "/init" ]

RUN pip install pipenv

RUN set -ex; \
    apk add --no-cache python2 nginx postgresql-client postgresql-dev gcc libc-dev g++ make nodejs npm libc-dev --virtual .build-deps; \
    apk --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --no-cache add leveldb leveldb-dev ; \
    npm config set unsafe-perm true ; \
    npm install -g @angular/cli ; \
    mkdir -p /data/api /data/ui ; \
    pip install uvicorn gunicorn

COPY Pipfile /data/api/
COPY Pipfile.lock /data/api/

COPY ui/package.json /data/ui/
COPY ui/package-lock.json /data/ui/

WORKDIR /data/ui
RUN npm install && ./node_modules/.bin/rn-nodeify --install process --hack
COPY ui /data/ui/
RUN ng build --prod

WORKDIR /data/api

RUN pipenv lock --requirements > requirements.txt && pip install -r requirements.txt

COPY config/services.d/ /etc/services.d/
COPY config/gunicorn_conf.py /gunicorn_conf.py
COPY config/nginx.conf /etc/nginx/nginx.conf
COPY config/nginx.vh.default.conf /etc/nginx/conf.d/default.conf

ENV GUNICORN_CONF       /gunicorn_conf.py
ENV DEFAULT_MODULE_NAME api.main:app_sio
ENV PYTHONPATH          /data

COPY api/* /data/api/
COPY shared /data/shared

WORKDIR /data

EXPOSE 80
