from .utils import invoke_rest_endpoint
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def health_check(config=None, *args, **kwargs):
    # template code. to be replaced with health check APIs and authentication method for the specific integration
    # sample health check URL
    
    return True
