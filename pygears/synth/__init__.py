from pygears import PluginBase, safe_bind, config
from .common import list_hdl_files, enum_hdl_files
from .yosys import synth as yosys_synth

__all__ = ['list_hdl_files', 'enum_hdl_files']


def synth(tool, top=None, outdir=None, language=None, **kwds):
    if tool not in config['synth/backend']:
        raise Exception(f'Unknown backend synth tool "{tool}".')

    return config['synth/backend'][tool](top=top,
                                         outdir=outdir,
                                         language=language,
                                         **kwds)


class SynthPlugin(PluginBase):
    @classmethod
    def bind(cls):
        config.define('synth/backend', default={'yosys': yosys_synth})
