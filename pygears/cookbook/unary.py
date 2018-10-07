from pygears import gear
from pygears.typing import Uint


@gear
def unary(din: Uint['w_data']) -> Uint['2**(int(w_data))']:
    '''Returns the unary representation of a binary number'''
    pass
