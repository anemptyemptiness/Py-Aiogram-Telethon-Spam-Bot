FROM python:3.11-slim-bullseye

WORKDIR /service

COPY requirements.txt .

RUN pip install --no-cache -r requirements.txt

COPY . /service/

RUN chmod 777 /service/*
RUN chmod a+x /service/docker/*.sh