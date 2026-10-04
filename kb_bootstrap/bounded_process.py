"""Finite process capture for the explicit ADR-018 adapter."""
from __future__ import annotations

import subprocess
import threading
import time


def run_bounded(argv, cwd, env, timeout=15, stdout_limit=1048576,
                stderr_limit=65536):
    """Return (stdout bytes, static reason); never expose child diagnostics."""
    try:
        process = subprocess.Popen(argv, cwd=str(cwd), env=env,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False)
    except OSError:
        return b"", "launch_failed"
    buffers = [bytearray(), bytearray()]
    limits = [stdout_limit, stderr_limit]
    overflow = threading.Event()

    def drain(stream, index):
        try:
            while True:
                chunk = stream.read1(4096)
                if not chunk:
                    break
                room = max(0, limits[index] - len(buffers[index]))
                buffers[index].extend(chunk[:room])
                if len(chunk) > room:
                    overflow.set()
        except (OSError, ValueError):
            overflow.set()

    readers = [threading.Thread(target=drain, args=(stream, index), daemon=True)
               for index, stream in enumerate((process.stdout, process.stderr))]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + timeout
    reason = ""
    while process.poll() is None:
        if overflow.is_set():
            reason = "output_limit"
            break
        if time.monotonic() >= deadline:
            reason = "timeout"
            break
        time.sleep(0.01)
    if reason:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        return b"", "termination_unconfirmed"
    for reader in readers:
        reader.join(timeout=2 if reason else max(0, deadline - time.monotonic()))
    if any(reader.is_alive() for reader in readers):
        # Descendants may retain pipes; do not pretend they were stopped.
        return b"", "termination_unconfirmed"
    process.stdout.close()
    process.stderr.close()
    if reason or overflow.is_set():
        return b"", reason or "output_limit"
    if process.returncode:
        return b"", "exit_nonzero"
    return bytes(buffers[0]), ""

