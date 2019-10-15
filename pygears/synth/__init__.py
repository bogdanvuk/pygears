from pygears import PluginBase, config
from .yosys import synth as yosys_synth


def synth(tool, top=None, outdir=None, language=None, **kwds):
    if tool not in config['synth/backend']:
        raise Exception(f'Unknown backend synth tool "{tool}".')

    return config['synth/backend'][tool](top=top,
                                         outdir=outdir,
                                         language=language,
                                         **kwds)


__all__ = ['synth']


class SynthPlugin(PluginBase):
    @classmethod
    def bind(cls):
        config.define('synth/backend', default={'yosys': yosys_synth})
