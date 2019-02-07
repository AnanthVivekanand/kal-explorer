FROM node:8.15.0-alpine

RUN npm config set unsafe-perm true
RUN npm install -g @angular/cli

WORKDIR /app

ADD package.json /app
ADD package-lock.json /app

RUN npm install

ADD . /app

RUN ng build --prod

RUN ls -l dist/ui


RUN apk add --no-cache nginx

COPY config/nginx.conf /etc/nginx/nginx.conf
COPY config/nginx.vh.default.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
