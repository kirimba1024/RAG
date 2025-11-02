#!/bin/sh
set -e

exec /sbin/tini -- /server server "$@"
