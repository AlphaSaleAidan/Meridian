#!/bin/sh
# Start go2rtc (ONVIF discovery + local frame API) in the background, then the
# local processing agent (YOLO on CPU -> POST counts). One process tree, one image.
set -e
go2rtc -config /app/go2rtc.yaml &
exec python3 /app/local_agent.py
