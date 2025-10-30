FROM python:3.10-alpine
LABEL io.figntigger.image.authors="christopher@hodgemcavaney.id.au" \
	maintainer="Christopher McAvaney <christopher@hodgemcavaney.id.au>" \
	description="MyAir to MQTT" \
	org.opencontainers.image.description="MyAir to MQTT" \
	org.opencontainers.image.authors="Christopher McAvaney <christopher@hodgemcavaney.id.au>" \
	org.opencontainers.image.url="https://git.figntigger.io/chrismc/-/packages/container/myair-to-mqtt" \
	org.opencontainers.image.source="https://git.figntigger.io/chrismc/myair-to-mqtt"

WORKDIR /code

COPY requirements.txt requirements.txt

# procps - needed for pgrep HEALTHCHECK command
# the "apk del build-dependencies" removes packages that were only needed for the build process
RUN apk add --no-cache procps \
	&& apk add --no-cache --virtual build-dependencies \
		gcc \
		python3-dev \
		musl-dev \
		linux-headers \
		git \
	&& pip install --no-cache-dir --requirement requirements.txt \
	&& apk del build-dependencies

COPY myair-to-mqtt.py myair-to-mqtt.py
COPY device_advantageair.py device_advantageair.py
CMD ["python", "myair-to-mqtt.py", "--conf", "/opt/myair-to-mqtt/etc/myair-to-mqtt.yml"]
HEALTHCHECK --start-period=10s --interval=10s CMD pgrep -x python > /dev/null || exit 1

# END OF FILE
