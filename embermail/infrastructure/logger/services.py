import datetime
import logging

import json_log_formatter
import ujson

logging.addLevelName(logging.CRITICAL, "FATAL")


class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    json_lib = ujson

    def json_record(self, message, extra, record):
        extra["level"] = record.__dict__["levelname"]
        extra["msg"] = message
        extra["logger"] = record.__dict__["name"]
        extra["func"] = record.__dict__["funcName"]
        extra["line"] = record.__dict__["lineno"]
        extra["time"] = datetime.datetime.now().isoformat()

        request = extra.pop("request", None)
        if request:
            extra["x_forward_for"] = request.META.get("X-FORWARD-FOR")
        return extra


class RecordDataJSONFormatter(json_log_formatter.JSONFormatter):
    json_lib = ujson

    def json_record(self, message, extra, record):
        extra["msg"] = message
        extra["date"] = datetime.datetime.now().strftime("%d-%m-%Y")
        extra["time"] = datetime.datetime.now().strftime("%H:%M:%S")
        extra["datetime"] = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        request = extra.pop("request", None)
        if request:
            extra["x_forward_for"] = request.META.get("X-FORWARD-FOR")
        return extra
