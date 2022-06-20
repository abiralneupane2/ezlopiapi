FROM python:3.8
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt requirements.txt

RUN apt-get update \
  && pip install -r requirements.txt \
  && apt-get clean

# copy project source code
COPY ./src .



CMD [ "python", "./main.py"]