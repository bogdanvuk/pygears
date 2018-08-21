from pygears import gear
from pygears.typing import Queue
from .ccat import ccat
from .czip import czip


@gear
def queue_wrap_from(din, qdin, *, fcat=czip):
    cat_data = fcat(qdin, din)

    return ccat(cat_data['data'][1], cat_data['eot']) \
        | Queue[din.dtype, qdin.dtype.lvl]
