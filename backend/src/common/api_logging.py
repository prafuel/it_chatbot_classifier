import logging
from pathlib import Path
from starlette.requests import Request
from .custom_logging import CustomizeLogger

# Create a fallback logger in case custom logger creation fails
fallback_logger = logging.getLogger("fallback")
fallback_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
fallback_logger.addHandler(handler)


def create_log(log_type: str):
    try:
        config_path = Path(__file__).with_name("logging_conf.json")
        custom_logger = CustomizeLogger.make_logger(config_path, log_type)
        return custom_logger
    except Exception as e:
        fallback_logger.error(f"Failed to create custom logger: {str(e)}")
        # Return the fallback logger if custom logger creation fails
        return fallback_logger


try:
    log = create_log("logger")
    logger = log.bind(logname="api")
except Exception as e:
    fallback_logger.error(f"Failed to bind logger: {str(e)}")
    logger = fallback_logger


async def logging_dependency(request: Request):
    try:
        logger.debug(f"{request.method} {request.url}")
        
        try:
            logger.debug("Params:")
            for name, value in request.path_params.items():
                logger.debug(f"{name}: {value}")
        except Exception as e:
            logger.error(f"Error logging path parameters: {str(e)}")
        
        try:
            logger.debug("Headers:")
            for name, value in request.headers.items():
                logger.debug(f"\t{name}: {value}")
        except Exception as e:
            logger.error(f"Error logging headers: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in logging_dependency: {str(e)}")