import json
import logging
import sys
from pathlib import Path
from loguru import logger
from app.common import constant


class InterceptHandler(logging.Handler):
    """
    Default handler from [loguru document](https://github.com/Delgan/loguru#unified-propagation-of-log-messages-including-standard-logging-module-and-uvicorn)
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomizeLogger:
    @classmethod
    def ensure_logs_directory(cls) -> Path:
        """
        Ensure the centralized logs directory exists.
        Uses /app/logs/ inside Docker (volume-mounted to ./logs/ on host),
        otherwise falls back to {repo_root}/logs/ for local development.
        Returns the absolute path to the logs directory.
        """
        docker_logs_dir = Path("/app/logs")
        if docker_logs_dir.parent.exists() and Path("/app/app/common").exists():
            # Inside Docker: write to the volume-mounted logs directory
            logs_dir = docker_logs_dir
        else:
            # Local dev: navigate from backend/src/common/ up to repo root
            current_file = Path(__file__).resolve()
            repo_root = current_file.parent.parent.parent.parent
            logs_dir = repo_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    @classmethod
    def resolve_log_path(cls, configured_path: str) -> Path:
        """
        Resolve log file path to absolute path in centralized logs directory.
        
        Args:
            configured_path: Path from config (e.g., "logs/access.log" or "access.log")
        
        Returns:
            Absolute path to log file in logsense/logs/
        """
        logs_dir = cls.ensure_logs_directory()
        
        # Extract just the filename if a path is provided
        path_obj = Path(configured_path)
        filename = path_obj.name
        
        # Return absolute path in centralized logs directory
        return logs_dir / filename

    @classmethod
    def make_logger(cls, config_path: Path, log_type: str):
        config = cls.load_logging_config(config_path)
        logging_config = config.get(log_type)

        # Resolve paths to absolute paths in centralized logs directory
        access_path = cls.resolve_log_path(logging_config.get("api_access_path"))
        error_path = cls.resolve_log_path(logging_config.get("api_error_path"))

        logger_obj = cls.customize_logging(
            access_path,
            api_error_path=error_path,
            retention=int(logging_config.get("retention")),
            rotation=logging_config.get("rotation"),
            format=logging_config.get("format"),
            api_name=logging_config.get("api_name"),
            error_filter=logging_config.get("error_filter"),
        )
        return logger_obj

    @classmethod
    def customize_logging(
        cls,
        api_access_path: Path,
        api_error_path: Path,
        rotation: str,
        retention: int,
        format: str,
        api_name: str,
        error_filter: str,
    ):
        # Intercept standard logging
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        
        # Set uvicorn loggers to use the InterceptHandler
        for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
            _logger = logging.getLogger(_log)
            _logger.handlers = [InterceptHandler()]
            _logger.propagate = False

        logger.remove()
        
        # Use a safe format that doesn't crash if 'logname' is missing
        safe_format = format.replace("{extra[logname]}", "{extra[logname]}") 
        # Actually, Loguru's default behavior is to fail if key is missing.
        # We'll bind a default logname to the base logger.
        
        logger.add(sys.stdout, enqueue=True, backtrace=True, format=format)
        
        # Combined log: captures all INFO+ logs regardless of 'logname'
        logger.add(
            str(api_access_path),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            format=format,
            filter=lambda record: record["level"].name in constant.LOG_LEVELS,
        )
        
        # Error log: captures all ERROR logs regardless of 'logname'
        logger.add(
            str(api_error_path),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            format=format,
            filter=lambda record: record["level"].name == "ERROR",
        )

        return logger.bind(logname="system", method=None)

    @classmethod
    def load_logging_config(cls, config_path):
        config = None
        with open(config_path) as config_file:
            config = json.load(config_file)
        return config
