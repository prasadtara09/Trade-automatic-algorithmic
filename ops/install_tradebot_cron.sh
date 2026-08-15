#!/usr/bin/env bash
# Run on the EC2 host:
# sudo bash ops/install_tradebot_cron.sh STREAM_IMAGE SCANNER_IMAGE

set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash ops/install_tradebot_cron.sh STREAM_IMAGE SCANNER_IMAGE"
  exit 1
fi

if [ "$#" -ne 2 ]; then
  echo "Provide the exact immutable image tags for stream and scanner."
  echo "Usage: sudo bash ops/install_tradebot_cron.sh STREAM_IMAGE SCANNER_IMAGE" >&2
  echo "Stream example: tara0674/fyers-tradebot-stream:build-30364363226" >&2
  echo "Scanner example: tara0674/fyers-tradebot-nifty-scan:build-30364363226" >&2
  exit 1
fi

STREAM_IMAGE="$1"
SCANNER_IMAGE="$2"
ENV_FILE="/opt/tradebot/.env"
LOG_DIR="/opt/tradebot/logs"

if [ ! -f "$ENV_FILE" ]; then
  echo "Create $ENV_FILE before installing the schedule."
  exit 1
fi

mkdir -p "$LOG_DIR"

# This script starts the live FYERS WebSocket stream each weekday morning.
cat > /usr/local/bin/start-tradebot-stream <<EOF
#!/usr/bin/env bash
set -e
docker rm -f fyers-tradebot-stream >/dev/null 2>&1 || true
docker pull "$STREAM_IMAGE"
docker run -d --rm \\
  --name fyers-tradebot-stream \\
  --env-file "$ENV_FILE" \\
  --mount type=bind,source="$LOG_DIR",target=/app/logs \\
  "$STREAM_IMAGE"
EOF
chmod 755 /usr/local/bin/start-tradebot-stream

# If EC2 starts after the 09:13 cron time, start the stream immediately when
# the Indian market is still open. If it starts before 09:13, cron handles it.
cat > /usr/local/bin/start-tradebot-if-market-open <<'EOF'
#!/usr/bin/env bash
set -e

WEEKDAY="$(TZ=Asia/Kolkata date +%u)"
MARKET_TIME="$(TZ=Asia/Kolkata date +%H%M)"

if [ "$WEEKDAY" -le 5 ] && [[ "$MARKET_TIME" > "0912" && "$MARKET_TIME" < "1545" ]]; then
  exec /usr/local/bin/start-tradebot-stream
fi

echo "EC2 started outside the weekday 09:13-15:45 IST stream window."
EOF
chmod 755 /usr/local/bin/start-tradebot-if-market-open

cat > /etc/systemd/system/tradebot-startup.service <<'EOF'
[Unit]
Description=Start the FYERS stream after EC2 boot when the Indian market is open
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/start-tradebot-if-market-open
TimeoutStartSec=5min

[Install]
WantedBy=multi-user.target
EOF

# This script performs the Friday one-time NIFTY 200 scan, then exits.
cat > /usr/local/bin/run-tradebot-scanner <<EOF
#!/usr/bin/env bash
set -e
docker pull "$SCANNER_IMAGE"
docker run --rm \\
  --name fyers-tradebot-nifty-scan \\
  --env-file "$ENV_FILE" \\
  "$SCANNER_IMAGE"
EOF
chmod 755 /usr/local/bin/run-tradebot-scanner

cat > /etc/cron.d/tradebot <<'EOF'
# All times below are India time, regardless of the EC2 host timezone.
CRON_TZ=Asia/Kolkata
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Monday-Friday: start the market stream at 09:13 and stop it at 15:45.
13 9 * * 1-5 root /usr/local/bin/start-tradebot-stream >> /opt/tradebot/logs/stream-start.log 2>&1
45 15 * * 1-5 root docker stop -t 30 fyers-tradebot-stream >> /opt/tradebot/logs/stream-stop.log 2>&1 || true

# Friday: calculate and upload the next weekly basket after market close.
50 15 * * 5 root /usr/local/bin/run-tradebot-scanner >> /opt/tradebot/logs/nifty-scan.log 2>&1
EOF
chmod 644 /etc/cron.d/tradebot

systemctl daemon-reload
systemctl enable tradebot-startup.service
systemctl enable --now cron 2>/dev/null || systemctl enable --now crond

echo "Cron schedule installed:"
echo "  Mon-Fri 09:13 IST - start FYERS stream"
echo "  Mon-Fri 15:45 IST - stop FYERS stream"
echo "  Friday  15:50 IST - run NIFTY 200 scanner"
echo "  EC2 boot during weekday market hours - start FYERS stream"
echo "Logs: $LOG_DIR"
