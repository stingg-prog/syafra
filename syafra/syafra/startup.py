import importlib


def repair_django_messages_module():
    try:
        messages = importlib.import_module('django.contrib.messages')
    except Exception:
        return

    if hasattr(messages, 'INFO') and hasattr(messages, 'add_message'):
        return

    try:
        api = importlib.import_module('django.contrib.messages.api')
        constants = importlib.import_module('django.contrib.messages.constants')
    except Exception:
        return

    for name in getattr(api, '__all__', ()):
        setattr(messages, name, getattr(api, name))

    for name in dir(constants):
        if name.isupper():
            setattr(messages, name, getattr(constants, name))
