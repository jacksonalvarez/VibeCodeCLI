from .python import PythonHandler
from .javascript import JavaScriptHandler
from .typescript import TypeScriptHandler
from .java import JavaHandler
from .cpp import CppHandler
from .c import CHandler
from .cs import CSharpHandler
from .go import GoHandler
from .rs import RustHandler
from .rb import RubyHandler
from .php import PHPHandler
from .html import HTMLHandler
from .css import CSSHandler
from .json import JSONHandler
from .md import MarkdownHandler
from .text import TextHandler
from .yaml import YAMLHandler

handlers = [
    PythonHandler,
    JavaScriptHandler,
    TypeScriptHandler,
    JavaHandler,
    CppHandler,
    CHandler,
    CSharpHandler,
    GoHandler,
    RustHandler,
    RubyHandler,
    PHPHandler,
    HTMLHandler,
    CSSHandler,
    JSONHandler,
    MarkdownHandler,
    TextHandler,
    YAMLHandler,
]

def get_handler(filename):
    for handler_cls in handlers:
        if handler_cls.matches(filename):
            return handler_cls()
    return None
