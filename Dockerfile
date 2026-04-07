FROM python:3.14-slim

WORKDIR /app

COPY app.py /app/app.py

ENV HOST=0.0.0.0
ENV PORT=9088
ENV LOG_FILE=/data/server.log

RUN mkdir -p /data

EXPOSE 9088

CMD ["python", "app.py"]
