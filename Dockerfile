FROM python:3.13

WORKDIR /app

VOLUME /app

COPY docker-entrypoint.sh requirements.txt uwsgi.ini /app/

COPY dist/ultra_tracker-*.whl /tmp/

RUN useradd -ms /bin/bash ultratracker

RUN python3 -m pip install --no-cache-dir -r requirements.txt /tmp/ultra_tracker-*.whl

USER ultratracker

CMD ["/app/docker-entrypoint.sh"]
