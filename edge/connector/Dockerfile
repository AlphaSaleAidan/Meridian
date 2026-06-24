# meridian-connector — one image the customer runs on an existing on-site PC.
# Bundles go2rtc (ONVIF discovery + WHIP publish) + the Python supervisor.
# One-line run (see README.md):
#   docker run -d --network host \
#     -e MERIDIAN_PAIRING_CODE=XXObtained-from-wizard \
#     -e MERIDIAN_API=https://api.meridian.tips \
#     ghcr.io/alphasaleaidan/meridian-connector
FROM alexxit/go2rtc:latest AS go2rtc

FROM python:3.12-slim
COPY --from=go2rtc /usr/local/bin/go2rtc /usr/local/bin/go2rtc
WORKDIR /app
COPY go2rtc.yaml connector.py entrypoint.sh ./
RUN chmod +x entrypoint.sh
# host networking is needed for ONVIF LAN discovery (multicast).
ENTRYPOINT ["./entrypoint.sh"]
