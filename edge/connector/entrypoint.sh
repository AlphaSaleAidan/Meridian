#!/bin/sh
# Start go2rtc (discovery + publish) in the background, then the supervisor.
set -e
go2rtc -config /app/go2rtc.yaml &
exec python3 /app/connector.py
