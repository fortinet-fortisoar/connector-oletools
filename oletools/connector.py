"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""

from connectors.core.connector import Connector
from connectors.core.connector import get_logger, ConnectorError
import json
from .custom_connector import CustomConnector

logger = get_logger("oletools")


class BaseConnector(Connector):
    """FortiSOAR Playbook calls this class first. Normmaly it calls the execute, check_health."""

    def _get_custom_connector(self, config: dict) -> CustomConnector:
        """Dummy function to get CustomConnector."""
        return CustomConnector()

    def execute(self, config: dict, operation: str, params: dict, **kwargs):
        """When an operation(action) is triggered, it calls this function to trigger an operation.

        Args:
            config (dict): configuration fields given by user.
            operation (str): operation(action) which the user calls in string, must match info.json operation field.
            params (dict): paremeters that the user gives in the action

        Returns:
            returns (dict, str): Advanced user always returns in json string or dict(json). Try to return as json.dumps(dict).
        """
        selected_operation = getattr(self._get_custom_connector(config), operation)
        if selected_operation:
            operation_output: dict = selected_operation(**params)
            try:
                json.dumps(operation_output)
                # try to serialize to json for type checking

                return operation_output
            except Exception as e:
                raise ConnectionError(
                    f"operation: {operation} returned data, but the data was not JSON serializable.\noutput of data: {operation_output}\nexception: {e}"
                )

        raise ConnectorError(f"operation: {operation} not found in custom_connector.py -> CustomConnector")

    def check_health(self, config: dict):
        """Check health is called when the new configuration is saved.

        Args:
            config (dict, optional): configuration fields given by user.
        """
        # To give error on the check_health you can trigger exception with below code.
        # raise ConnectionError("this is an error!")
        conn = self._get_custom_connector(config)
        return
