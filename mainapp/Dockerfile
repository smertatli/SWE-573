# pull official base image
FROM python:3.10.0a4-slim-buster
RUN echo "@community http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories \
&& apk add py3-pandas@community
ENV PYTHONPATH=/usr/lib/python3.8/site-packages

# set work directory
WORKDIR /usr/src/mainapp

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev



# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy entrypoint.sh
COPY ./entrypoint.sh .

# copy proj ect
COPY . .

# run entrypoint.sh
ENTRYPOINT ["/usr/src/mainapp/entrypoint.sh"]