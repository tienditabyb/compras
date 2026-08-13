FROM alpine:latest
RUN apk add --no-cache ca-certificates unzip
ADD https://github.com/pocketbase/pocketbase/releases/download/v0.25.0/pocketbase_0.25.0_linux_amd64.zip /tmp/pocketbase.zip
RUN unzip /tmp/pocketbase.zip -d /usr/local/bin/ && rm /tmp/pocketbase.zip
RUN mkdir -p /pb_data
COPY pb_data /pb_data
EXPOSE 8080
CMD ["/bin/sh", "-c", "/usr/local/bin/pocketbase superuser upsert $PB_ADMIN_EMAIL $PB_ADMIN_PASSWORD && /usr/local/bin/pocketbase serve --http=0.0.0.0:8080 --dir=/pb_data"]
