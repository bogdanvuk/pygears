import importlib
import os
import jinja2
from pygears.typing import bitw


def format_list(list_, pattern):
    return [pattern % s for s in list_]


def keymap(list_, key):
    return [item[key] for item in list_]


def isinput(list_):
    return [item for item in list_ if item["modport"] == "consumer"]


def isoutput(list_):
    return [item for item in list_ if item["modport"] == "producer"]


def startswith(field, s):
    return field.startswith(s)


def import_from(module, name):
    module = importlib.import_module(module)
    return getattr(module, name)


def import_(module):
    return importlib.import_module(module)


class TemplateEnv:
    def __init__(self, basedir):
        self.basedir = basedir
        self.templates = {}
        self.jenv = jinja2.Environment(extensions=['jinja2.ext.do'],
                                       trim_blocks=True,
                                       lstrip_blocks=True,
                                       undefined=jinja2.StrictUndefined)

        self.jenv.globals.update(zip=zip,
                                 len=len,
                                 int=int,
                                 bitw=bitw,
                                 enumerate=enumerate,
                                 import_from=import_from,
                                 import_=import_)

        self.jenv.filters['format_list'] = format_list
        self.jenv.filters['keymap'] = keymap
        self.jenv.filters['isinput'] = isinput
        self.jenv.filters['isoutput'] = isoutput
        self.jenv.tests['startswith'] = startswith

        self.snippets = self.load(self.basedir, 'snippet.j2').module

    def load(self, tmplt_dir, tmplt_fn):
        key = os.path.join(self.basedir, tmplt_dir, tmplt_fn)
        if key not in self.templates:
            self.jenv.loader = jinja2.FileSystemLoader(
                [self.basedir, tmplt_dir])
            template = self.jenv.get_template(tmplt_fn)
            self.templates[key] = template

        return self.templates[key]

    def render_string(self, string, context):
        return self.jenv.from_string(string).render(context)

    def render_local(self, fn, tmplt_fn, context):
        return self.render(os.path.dirname(fn), tmplt_fn, context)

    def render(self, tmplt_dir, tmplt_fn, context):
        return self.load(tmplt_dir, tmplt_fn).render(context)
