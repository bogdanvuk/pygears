from pygears.core.gear import gear
from pygears import Queue


@gear(
    sv_param_kwds=['lvl'], enablement='{din_lvl} >= {lvl}')
def qenvelope(din: Queue['{din_t}', '{din_lvl}'], *,
              lvl) -> 'Queue[Unit, {lvl}]':
    pass
