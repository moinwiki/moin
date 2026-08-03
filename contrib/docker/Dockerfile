FROM python:3.14.6-trixie

ARG wheel

# pin hypercorn to version 0.17.3 because of known issues with the latest release 0.18.0
RUN pip install --no-cache-dir hypercorn==0.17.3

# install the moin 2.x python wheel
COPY dist/$wheel /tmp/$wheel
RUN pip install --no-cache-dir /tmp/$wheel
RUN rm /tmp/$wheel

# create an unprivileged user
RUN groupadd --non-unique --gid 1000 moin && adduser --disabled-password --uid 1000 --gid 1000 moin
RUN mkdir /app

# copy configuration files
COPY contrib/docker/config.toml /app
COPY wikiconfig.py /app
COPY wiki /app/wiki

RUN chown -R moin:moin /app

USER moin

WORKDIR /app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# run moin as WSGI application in hypercorn
CMD ["hypercorn", "--config", "config.toml", "wsgi:moin.app:create_app()"]
