from pygears import gear
from pygears.typing import Union, Unit


@gear
def valve(din: Union['Tdin', Unit]) -> b'Tdin':
    pass
