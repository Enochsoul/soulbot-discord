FROM python:3.10

WORKDIR ./discordbot

RUN git clone -b multi-dev https://github.com/Enochsoul/soulbot-discord.git .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

ARG SOURCE_CONFIG_FILE=soulbot.conf
COPY $SOURCE_CONFIG_FILE soulbot.conf

CMD python ./soulbot.py