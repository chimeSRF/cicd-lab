"""NC Connection Plugin"""
from typing import Any, Dict, Optional

from ncdiff import manager

CONNECTION_NAME = "nc"


class Nc:
    """This plugin connects to the devices via NETCONF using ncdiff library."""

    def open(
        self,
        hostname: str,
        username: str,
        password: Optional[str],
        port: Optional[int] = 830,
        platform: Optional[str] = "default",
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        extras = extras if extras is not None else {}
        parameters: Dict[str, Any] = {
            "host": hostname,
            "username": username,
            "password": password,
            "port": port,
        }
        parameters.update(extras)
        self.connection = manager.connect(**parameters)
        self.connection.scan_models(folder=f"./yang/{hostname}")

    def close(self) -> None:
        self.connection.close_session()
