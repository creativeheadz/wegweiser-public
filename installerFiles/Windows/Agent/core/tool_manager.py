import os
import sys
import platform
import asyncio
import tarfile
import logging
import shutil
import urllib.request
from typing import Dict, Any, Optional

try:
    import aiohttp  # type: ignore
except ImportError:
    aiohttp = None  # type: ignore

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages on-demand downloading, unpacking, and execution of tools."""

    def __init__(self, base_dir: str, server_url: str):
        self.tools_dir = os.path.join(base_dir, "Tools")
        self.server_url = server_url
        os.makedirs(self.tools_dir, exist_ok=True)

        # A registry of known tools that can be downloaded.
        self.registered_tools = {
            "loki": {
                "executable_path": "Loki/loki_wrapper.py",
                "package_name": "loki.tar.gz",
                "entry_point": "loki_wrapper.py",
            }
        }

    async def get_tool_executable(self, tool_name: str) -> Optional[str]:
        """Gets the path to a tool's executable, downloading it if necessary.
        Returns the path to the entry point script.
        """
        if tool_name not in self.registered_tools:
            logger.error(f"Tool '{tool_name}' is not registered.")
            return None

        tool_info = self.registered_tools[tool_name]
        # The executable path is the entry point script for python-based tools
        expected_path = os.path.join(self.tools_dir, tool_info["executable_path"])

        if os.path.exists(expected_path):
            logger.info(f"Tool '{tool_name}' found at {expected_path}")
            return expected_path

        logger.info(f"Tool '{tool_name}' not found locally, attempting download.")
        return await self.download_and_unpack_tool(tool_name)

    async def download_and_unpack_tool(self, tool_name: str) -> Optional[str]:
        """Downloads and unpacks a tool from the server."""
        tool_info = self.registered_tools[tool_name]
        package_name = tool_info["package_name"]
        download_url = f"https://{self.server_url}/download/tools/{package_name}"
        local_path = os.path.join(self.tools_dir, package_name)

        logger.info(f"Downloading {tool_name} from {download_url}...")
        loop = asyncio.get_event_loop()
        try:
            if aiohttp is not None:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as response:
                        if response.status == 200:
                            with open(local_path, "wb") as f:
                                while True:
                                    chunk = await response.content.read(8192)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                        else:
                            logger.error(
                                f"Failed to download tool {tool_name}. Status: {response.status}"
                            )
                            return None
            else:
                logger.info("aiohttp not available, falling back to urllib for tool download")
                await loop.run_in_executor(
                    None, self._download_with_urllib, download_url, local_path
                )

            logger.info(f"Unpacking {local_path}...")
            # tarfile operations are blocking, run in an executor
            await loop.run_in_executor(None, self._extract_tar, local_path, self.tools_dir)

            os.remove(local_path)

            expected_path = os.path.join(self.tools_dir, tool_info["executable_path"])

            if os.path.exists(expected_path):
                logger.info(f"Successfully downloaded and unpacked {tool_name}.")
                return expected_path

            logger.error(f"Executable not found at {expected_path} after unpacking.")
            shutil.rmtree(os.path.join(self.tools_dir, tool_name), ignore_errors=True)
            return None

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(
                f"An error occurred while downloading/unpacking {tool_name}: {e}",
                exc_info=True,
            )
            if os.path.exists(local_path):
                os.remove(local_path)
            return None

    def _extract_tar(self, tar_path: str, extract_path: str) -> None:
        """Blocking function to extract a tar.gz file."""
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=extract_path)

    def _download_with_urllib(self, url: str, local_path: str) -> None:
        """Blocking download implementation using urllib as a fallback."""
        with urllib.request.urlopen(url) as response, open(local_path, "wb") as f:
            shutil.copyfileobj(response, f)

    async def run_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a tool with the given parameters.

        For Python tools, it ensures the correct virtual environment is used.
        """
        entry_point_path = await self.get_tool_executable(tool_name)
        if not entry_point_path:
            return {
                "status": "error",
                "message": f"Tool '{tool_name}' not available or failed to download.",
            }

        # For python tools, we need to find the python executable in the agent's venv
        agent_venv_python = os.path.join(
            os.path.dirname(sys.executable),
            "python.exe" if platform.system() == "Windows" else "python3",
        )

        if not os.path.exists(agent_venv_python):
            agent_venv_python = sys.executable  # fallback to current python

        # Construct the command line arguments for the tool
        args: list[str] = []
        for key, value in parameters.items():
            flag = f"--{key}"
            # Treat boolean values as flags (store_true-style)
            if isinstance(value, bool):
                if value:
                    args.append(flag)
                continue
            # Allow list/tuple values for repeated flags
            if isinstance(value, (list, tuple)):
                for item in value:
                    args.append(flag)
                    args.append(str(item))
                continue
            args.append(flag)
            args.append(str(value))

        command = [agent_venv_python, entry_point_path] + args

        logger.info(f"Running tool command: {' '.join(command)}")

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        logger.info(f"Tool '{tool_name}' finished with exit code {proc.returncode}")

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "stdout": stdout.decode(errors="ignore"),
            "stderr": stderr.decode(errors="ignore"),
            "returncode": proc.returncode,
        }

