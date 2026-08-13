FROM alpine:latest

RUN apk add --no-cache ca-certificates unzip

# Descargar PocketBase versión 0.25.0 (puedes cambiar la versión si quieres)
ADD https://github.com/pocketbase/pocketbase/releases/download/v0.25.0/pocketbase_0.25.0_linux_amd64.zip /tmp/pocketbase.zip
RUN unzip /tmp/pocketbase.zip -d /usr/local/bin/ && rm /tmp/pocketbase.zip

# Crear el directorio donde se montará el volumen (aunque luego se monte encima)
RUN mkdir -p /pb_data

EXPOSE 8080

# Comando de inicio: si las variables de entorno no están definidas, se usa el puerto 8080 y el directorio /pb_data
CMD ["/bin/sh", "-c", "if [ -n \"$PB_ADMIN_EMAIL\" ] && [ -n \"$PB_ADMIN_PASSWORD\" ]; then /usr/local/bin/pocketbase superuser upsert $PB_ADMIN_EMAIL $PB_ADMIN_PASSWORD; fi && /usr/local/bin/pocketbase serve --http=0.0.0.0:8080 --dir=/pb_data"]
