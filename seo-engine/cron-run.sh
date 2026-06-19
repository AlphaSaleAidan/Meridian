#!/usr/bin/env bash
# Wrapper so cron lines stay tidy and env loads consistently.
# Usage: cron-run.sh <script.mjs> [args...]
cd /root/meridian-seo/seo-engine || exit 1
exec /usr/bin/node --env-file=.env "$@"
