from .svgen import svgen
from .connect import svgen_connect
from .generate import svgen_generate
from .inst import svgen_inst

from pygears.registry import load_plugin_folder
import os
load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))


__all__ = ['svgen', 'svgen_inst', 'svgen_connect', 'svgen_generate']
