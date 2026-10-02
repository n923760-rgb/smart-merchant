import json
import logging


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = {"level": record.levelname, "message": record.getMessage()}
        for key in (
            "request_id",
            "user_id",
            "organization_id",
            "method",
            "route",
            "status",
            "duration_ms",
        ):
            if hasattr(record, key):
                fields[key] = getattr(record, key)
        return json.dumps(fields)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
