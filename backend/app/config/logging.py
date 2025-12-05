import logging

log_format = (
    "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | "
    "%(funcName)s | %(message)s"
)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(log_format, "%Y-%m-%d %H:%M:%S"))

root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(handler)
root.propagate = False

logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
