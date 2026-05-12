#!/usr/bin/env python3
"""Swarm Trainer Daemon — runs autonomously 24/7, training every 5 minutes."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ai.swarm_trainer import get_swarm_trainer


async def main():
    trainer = get_swarm_trainer()
    print(f"[SwarmTrainer] Starting autonomous training loop (300s interval)")
    print(f"[SwarmTrainer] Scores file: {trainer._scores}")
    await trainer.start_autonomous(interval_seconds=300)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SwarmTrainer] Stopped")
