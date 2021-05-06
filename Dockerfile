FROM python:alpine
RUN pip install requests
RUN mkdir /logs && mkdir /config
RUN apk add --update docker openrc
RUN rc-update add docker boot
COPY . .
ENTRYPOINT ["python", "-u", "main.py"]