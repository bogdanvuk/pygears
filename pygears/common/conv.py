from pygears.core.gear import Gear, gear
from pygears import Int, Uint
from pygears.typing.base import TypingMeta
from pygears.core.intf import IntfOperPlugin


class Conv(Gear):
    def infer_params_and_ftypes(self):

        ftypes, params = super().infer_params_and_ftypes()

        din_type = self.args[0].dtype
        dout_type = ftypes[-1]

        if issubclass(dout_type, Int) and (not dout_type.is_specified()):
            if issubclass(din_type, Uint):
                self.ftypes[-1] = Int[int(din_type) + 1]
            elif issubclass(din_type, Int):
                self.ftypes[-1] = din_type

        return ftypes, params


@gear(gear_cls=Gear, sv_param_kwds=[])
def conv(din, *, cast_type) -> '{cast_type}':
    pass


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        return conv(
            self, cast_type=other, name=f'conv_{self.producer.basename}')
    else:
        return other.__ror__(self)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
