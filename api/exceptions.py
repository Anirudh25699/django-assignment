from django.core.exceptions import RequestDataTooBig
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = "The uploaded file exceeds the 5 MiB limit."
    default_code = "payload_too_large"


def exception_handler(exc, context):
    if isinstance(exc, RequestDataTooBig):
        exc = PayloadTooLarge("Request body is too large.")
    return drf_exception_handler(exc, context)
