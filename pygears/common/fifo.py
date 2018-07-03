from pygears import gear


@gear(svgen={'svmod_fn': 'fifo.sv'})
def fifo(din: 'width', *, depth=2) -> b'width':
    '''For this implementation depth must be a power of 2'''
    pass
