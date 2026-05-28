"""
Evolver bridge — triggers the GEP self-evolution service from Python.

The evolver runs as a standalone Node.js daemon at services/evolver/.
This client provides a Python interface for triggering evolution cycles,
reviewing pending changes, and solidifying approved mutations.
"""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("meridian.services.evolver")

EVOLVER_DIR = Path(__file__).resolve().parents[2] / "services" / "evolver"
EVOLVER_NODE = os.environ.get("EVOLVER_NODE_PATH", "node")


class EvolverClient:

    def __init__(self):
        self._dir = EVOLVER_DIR
        self._available = (self._dir / "index.js").exists()
        if not self._available:
            logger.warning("Evolver service not found at %s", self._dir)

    @property
    def is_available(self) -> bool:
        return self._available

    async def run_cycle(self, target: str | None = None) -> dict[str, Any]:
        """Run a single evolution cycle. Returns the cycle result."""
        cmd = [EVOLVER_NODE, "index.js", "run"]
        if target:
            cmd.extend(["--target", target])
        return await self._exec(cmd)

    async def review(self) -> dict[str, Any]:
        """Review pending evolved changes before solidifying."""
        return await self._exec([EVOLVER_NODE, "index.js", "review"])

    async def solidify(self) -> dict[str, Any]:
        """Confirm and merge evolved changes into the codebase."""
        return await self._exec([EVOLVER_NODE, "index.js", "solidify"])

    async def status(self) -> dict[str, Any]:
        """Get evolver daemon status."""
        return await self._exec([EVOLVER_NODE, "index.js", "status"])

    async def _exec(self, cmd: list[str]) -> dict[str, Any]:
        if not self._available:
            return {"error": "evolver not available", "ok": False}
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self._dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "EVOLVER_JSON_OUTPUT": "1"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode().strip()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {
                    "ok": proc.returncode == 0,
                    "output": output,
                    "stderr": stderr.decode().strip(),
                }
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return {"error": "evolver timed out after 120s", "ok": False}
        except Exception as e:
            logger.error("Evolver exec failed: %s", e)
            return {"error": str(e), "ok": False}


_client: EvolverClient | None = None


def get_evolver() -> EvolverClient:
    global _client
    if _client is None:
        _client = EvolverClient()
    return _client
