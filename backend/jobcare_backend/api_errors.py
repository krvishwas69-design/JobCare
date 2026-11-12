"""Make every API error look like {"detail": "<readable message>"} so the UI can show it."""
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


def _first_message(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'code':
                continue
            msg = _first_message(value)
            if msg:
                return msg if key in ('detail', 'non_field_errors') else f'{key}: {msg}'
    elif isinstance(data, (list, tuple)):
        for item in data:
            msg = _first_message(item)
            if msg:
                return msg
    elif data:
        return str(data)
    return ''


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is not None and isinstance(response.data, (dict, list)):
        code = response.data.get('code') if isinstance(response.data, dict) else None
        payload = {'detail': _first_message(response.data) or 'Request failed.'}
        if code:
            payload['code'] = str(code)
        response.data = payload
    return response
