FROM python:3.14-slim

WORKDIR /app

COPY app.py /app/app.py

ENV PORT=80
ENV LOG_FILE=/data/server.log

RUN mkdir -p /data/dmr

EXPOSE 80

CMD ["python", "app.py"]
