"""Custom tool runner for executing user-provided Python tools in a subprocess.

Security note: This runner is intended for development and controlled environments.
It executes arbitrary Python code in a separate process with timeouts and no
network access guarantees at the OS level here. For production, enforce stronger
isolation (e.g., Firecracker, gVisor, seccomp) and rigorous validation.
"""

import asyncio
import tempfile
import os
from typing import Optional
from fastapi import HTTPException, status


class CustomToolRunner:
    """Run custom Python tool code as a separate process with a simple contract.

    Contract: The tool code must define a function `run(input_str: str) -> str`.
    We generate a small wrapper that imports the function and prints its output.
    The runner passes the input as a string via CLI arg, and captures stdout.
    """

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def execute(self, code: str, tool_input: str) -> str:
        """
        Execute custom tool code with the given input and return stdout output.

        Args:
            code: Python source code implementing `def run(input_str: str) -> str`.
            tool_input: String input to pass to run().

        Returns:
            stdout string from the tool wrapper (the result of run()).
        """
        if not code or "def run(" not in code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom tool code must define run(input_str: str) -> str",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            tool_path = os.path.join(tmpdir, "tool_impl.py")
            wrapper_path = os.path.join(tmpdir, "runner.py")

            # Write tool code
            with open(tool_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Minimal wrapper that imports run and prints result
            wrapper = (
                "import sys\n"
                "sys.path.insert(0, '.')\n"
                "from tool_impl import run\n"
                "if __name__ == '__main__':\n"
                "    inp = sys.stdin.read()\n"
                "    out = run(inp)\n"
                "    if out is None:\n"
                "        out = ''\n"
                "    print(out)\n"
            )
            with open(wrapper_path, "w", encoding="utf-8") as f:
                f.write(wrapper)

            # Execute subprocess with stdin as tool_input
            proc = await asyncio.create_subprocess_exec(
                "python", wrapper_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=tool_input.encode("utf-8")),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail=f"Custom tool execution timed out after {self.timeout}s",
                )

            if proc.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Custom tool failed (code {proc.returncode}): {stderr.decode('utf-8')[:1000]}",
                )

            return stdout.decode("utf-8")

