"""Small framework boundary for offline tests without a running AstrBot."""

import importlib.util
import logging
import sys
from types import ModuleType


if importlib.util.find_spec("astrbot") is None:
    astrbot = ModuleType("astrbot")
    api = ModuleType("astrbot.api")
    components = ModuleType("astrbot.api.message_components")
    api.logger = logging.getLogger("ppnai-test")

    class BaseMessageComponent:
        pass

    class Image(BaseMessageComponent):
        @classmethod
        def fromBytes(cls, data):
            image = cls()
            image.data = data
            return image

    class Reply(BaseMessageComponent):
        def __init__(self, chain=None):
            self.chain = chain or []

    components.BaseMessageComponent = BaseMessageComponent
    components.Image = Image
    components.Reply = Reply
    api.message_components = components
    astrbot.api = api
    sys.modules.update({
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.message_components": components,
    })
