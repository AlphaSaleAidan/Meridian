#!/bin/bash
# Start all 3 autonomous daemons — Swarm Trainer, Scraper, Evolver
# Usage: ./scripts/start-all-daemons.sh
#   Stop: ./scripts/start-all-daemons.sh stop
#   Status: ./scripts/start-all-daemons.sh status

cd /root/Meridian

LOG_DIR="logs"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

start_daemons() {
    echo "Starting Meridian autonomous daemons..."

    # 1. Swarm Trainer (Python, 5-min cycle)
    if [ -f "$PID_DIR/swarm-trainer.pid" ] && kill -0 "$(cat "$PID_DIR/swarm-trainer.pid")" 2>/dev/null; then
        echo "  [SwarmTrainer] Already running (PID $(cat "$PID_DIR/swarm-trainer.pid"))"
    else
        nohup python3 scripts/swarm-trainer-daemon.py >> "$LOG_DIR/swarm-trainer.log" 2>&1 &
        echo $! > "$PID_DIR/swarm-trainer.pid"
        echo "  [SwarmTrainer] Started (PID $!)"
    fi

    # 2. Business Knowledge Scraper (Python, 6-hour cycle)
    if [ -f "$PID_DIR/scraper.pid" ] && kill -0 "$(cat "$PID_DIR/scraper.pid")" 2>/dev/null; then
        echo "  [Scraper] Already running (PID $(cat "$PID_DIR/scraper.pid"))"
    else
        nohup python3 scripts/scraper-daemon.py >> "$LOG_DIR/scraper.log" 2>&1 &
        echo $! > "$PID_DIR/scraper.pid"
        echo "  [Scraper] Started (PID $!)"
    fi

    # 3. Evolver (Node.js, 4-hour cycle)
    if [ -f "$PID_DIR/evolver.pid" ] && kill -0 "$(cat "$PID_DIR/evolver.pid")" 2>/dev/null; then
        echo "  [Evolver] Already running (PID $(cat "$PID_DIR/evolver.pid"))"
    else
        nohup bash scripts/evolver-daemon.sh >> "$LOG_DIR/evolver.log" 2>&1 &
        echo $! > "$PID_DIR/evolver.pid"
        echo "  [Evolver] Started (PID $!)"
    fi

    echo ""
    echo "All daemons launched. Logs:"
    echo "  tail -f logs/swarm-trainer.log"
    echo "  tail -f logs/scraper.log"
    echo "  tail -f logs/evolver.log"
}

stop_daemons() {
    echo "Stopping Meridian autonomous daemons..."
    for name in swarm-trainer scraper evolver; do
        pid_file="$PID_DIR/$name.pid"
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null
                # Kill child processes too
                pkill -P "$pid" 2>/dev/null
                echo "  [$name] Stopped (PID $pid)"
            else
                echo "  [$name] Not running (stale PID)"
            fi
            rm -f "$pid_file"
        else
            echo "  [$name] No PID file"
        fi
    done
}

status_daemons() {
    echo "Meridian Autonomous Daemons:"
    echo "──────────────────────────────────────"
    for name in swarm-trainer scraper evolver; do
        pid_file="$PID_DIR/$name.pid"
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            pid=$(cat "$pid_file")
            uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
            echo "  [$name] RUNNING (PID $pid, uptime: $uptime)"
        else
            echo "  [$name] STOPPED"
        fi
    done
    echo "──────────────────────────────────────"
    echo ""
    echo "Recent log tails:"
    for log in swarm-trainer scraper evolver; do
        if [ -f "$LOG_DIR/$log.log" ]; then
            echo "  --- $log ---"
            tail -3 "$LOG_DIR/$log.log" 2>/dev/null | sed 's/^/  /'
        fi
    done
}

case "${1:-start}" in
    start) start_daemons ;;
    stop) stop_daemons ;;
    restart) stop_daemons; sleep 2; start_daemons ;;
    status) status_daemons ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac
