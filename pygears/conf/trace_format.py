import os
from enum import IntEnum

from traceback import extract_stack, extract_tb

from pygears.definitions import ROOT_DIR

from .pdb_patch import patch_pdb, unpatch_pdb
from .registry import PluginBase, reg


class TraceLevel(IntEnum):
    debug = 0
    user = 1


def set_trace_level(var, val):
    var._val = val
    if val == TraceLevel.user:
        patch_pdb()
    else:
        unpatch_pdb()


def parse_trace(s):
    if reg['trace/level'] == TraceLevel.debug:
        return s
    else:
        trace_fn = os.path.abspath(s.filename)
        is_internal = any(trace_fn.startswith(d) for d in reg['trace/ignore'])

        is_decorator_gen = '<decorator-gen' in trace_fn

        if is_internal or is_decorator_gen:
            return None

        return s


def enum_formated_stack_frames(summary):
    for frame, display in zip(summary, summary.format()):
        if parse_trace(frame):
            yield display


def enum_traceback(tr):
    yield from enum_formated_stack_frames(extract_tb(tr))


def enum_stacktrace():
    yield from enum_formated_stack_frames(extract_stack())


class TraceFormatPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['trace/hooks'] = []

        reg.confdef('trace/level', setter=set_trace_level, default=TraceLevel.debug)

        reg.confdef(
            'trace/ignore',
            default=[
                os.path.join(ROOT_DIR, d) for d in ['core', 'conf', 'sim', 'hls', 'hdl']
            ] + [os.path.dirname(os.__file__)])
