import importlib
import ctypes
import re
import os
import sys
import jinja2
from jinja2.ext import Extension
from pygears.typing import bitw, code, decode
from textwrap import dedent
from io import StringIO


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


def debug(text):
    print(text)
    return ''


def get_port_config(modport, type_, name):
    return {
        'modport': modport,
        'name': name,
        'size': 1,
        'type': type_,
        'width': type_.width,
        'local_type': type_
    }


def get_port_intfs(node):
    intfs = []

    for p in node.in_ports:
        intfs.append(get_port_config('consumer', type_=p.dtype, name=p.basename))

    for p in node.out_ports:
        intfs.append(get_port_config('producer', type_=p.dtype, name=p.basename))

    return intfs

class TemplateEnv:
    def __init__(self, basedir):
        self.basedir = basedir
        self.templates = {}
        self.jenv = jinja2.Environment(
            extensions=['jinja2.ext.do', PythonExtension],
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined)

        self.jenv.globals.update(
            zip=zip,
            len=len,
            int=int,
            max=max,
            tuple=tuple,
            isinstance=isinstance,
            bitw=bitw,
            enumerate=enumerate,
            import_from=import_from,
            import_=import_,
            code=code,
            decode=decode)

        self.jenv.filters['format_list'] = format_list
        self.jenv.filters['keymap'] = keymap
        self.jenv.filters['isinput'] = isinput
        self.jenv.filters['isoutput'] = isoutput
        self.jenv.filters['debug'] = debug
        self.jenv.tests['startswith'] = startswith

    # TODO: Revisit this function
    def port_intfs(self, node):
        return get_port_intfs(node)

    def load(self, tmplt_dir, tmplt_fn):
        key = os.path.join(self.basedir, tmplt_dir, tmplt_fn)
        if key not in self.templates:
            self.jenv.loader = jinja2.FileSystemLoader([self.basedir, tmplt_dir])
            template = self.jenv.get_template(tmplt_fn)
            self.templates[key] = template

        return self.templates[key]

    def render_string(self, string, context):
        return self.jenv.from_string(string).render(context)

    def render_local(self, fn, tmplt_fn, context):
        return self.render(os.path.dirname(fn), tmplt_fn, context)

    def render(self, tmplt_dir, tmplt_fn, context):
        return self.load(tmplt_dir, tmplt_fn).render(context)

var_name_regex = re.compile(r"l_(\d+)_(.+)")


class PythonExtension(Extension):
    # a set of names that trigger the extension.
    tags = {'py'}

    def __init__(self, environment: jinja2.Environment):
        super().__init__(environment)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endpy'], drop_needle=True)
        return jinja2.nodes.CallBlock(self.call_method('_exec_python',
                                                [jinja2.nodes.ContextReference(), jinja2.nodes.Const(lineno), jinja2.nodes.Const(parser.filename)]),
                               [], [], body).set_lineno(lineno)

    def _exec_python(self, ctx, lineno, filename, caller):
        # Remove access indentation
        code = dedent(caller())

        # Compile the code.
        compiled_code = compile("\n"*(lineno-1) + code, filename, "exec")

        # Create string io to capture stdio and replace it.
        sout = StringIO()
        stdout = sys.stdout
        sys.stdout = sout

        try:
            # Execute the code with the context parents as global and context vars and locals.
            exec(compiled_code, ctx.parent, ctx.vars)
        except Exception:
            raise
        finally:
            # Restore stdout whether the code crashed or not.
            sys.stdout = stdout

        # Get a set of all names in the code.
        code_names = set(compiled_code.co_names)

        # The the frame in the jinja generated python code.
        caller_frame = sys._getframe(2)

        # Loop through all the locals.
        for local_var_name in caller_frame.f_locals:
            # Look for variables matching the template variable regex.
            match = re.match(var_name_regex, local_var_name)
            if match:
                # Get the variable name.
                var_name = match.group(2)

                # If the variable's name appears in the code and is in the locals.
                if (var_name in code_names) and (var_name in ctx.vars):
                    # Copy the value to the frame's locals.
                    caller_frame.f_locals[local_var_name] = ctx.vars[var_name]
                    # Do some ctypes vodo to make sure the frame locals are actually updated.
                    ctx.exported_vars.add(var_name)
                    ctypes.pythonapi.PyFrame_LocalsToFast(
                        ctypes.py_object(caller_frame),
                        ctypes.c_int(1))

        # Return the captured text.
        return sout.getvalue()

