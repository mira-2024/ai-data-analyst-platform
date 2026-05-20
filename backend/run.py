"""
Windows-safe uvicorn runner.

Python's default SelectorEventLoop on Windows has a hard 512-FD limit.
ProactorEventLoop uses Windows IOCP and has no such limit.

Run this instead of `uvicorn main:app --reload`:
    python run.py
"""

import asyncio
import sys

# Must be set BEFORE uvicorn imports anything
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,       # reload + multiprocessing + Windows = FD exhaustion
        loop="asyncio",     # honours the ProactorEventLoop policy above
        log_level="info",
    )
