from .svgen import svgen
from .inst import register_sv_paths
from .generate import svgen_generate

from pygears.registry import load_plugin_folder
import os
load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))


__all__ = ['svgen', 'svgen_generate', 'register_sv_paths']
