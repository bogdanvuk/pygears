from pygears import gear
from pygears.typing import Array


@gear
def serialize(din: Array['w_din', 'size']) -> b'w_din':
    pass
