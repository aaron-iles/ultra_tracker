FROM python:3.13

WORKDIR /app

VOLUME /app

COPY docker-entrypoint.sh requirements.txt uwsgi.ini /app/

COPY .tox/.pkg/dist/ultra_tracker-*.tar.gz /tmp/

RUN useradd -ms /bin/bash uwsgi

RUN python3 -m pip install --no-cache-dir -r requirements.txt /tmp/ultra_tracker-*.tar.gz

COPY src/ultra_tracker/ /usr/lib/python3.13/ultra_tracker/

CMD ["/app/docker-entrypoint.sh"]
