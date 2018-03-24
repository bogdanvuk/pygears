from pygears.core.gear import Gear, gear
from pygears import Tuple


class CCat(Gear):
    def infer_params_and_ftypes(self):
        ftypes, params = super().infer_params_and_ftypes()
        ftypes[-1] = Tuple[tuple(t.dtype for t in self.args)]

        return ftypes, params


@gear(gear_cls=CCat)
def ccat(*din: '{{w_data{0}}}'):
    pass
