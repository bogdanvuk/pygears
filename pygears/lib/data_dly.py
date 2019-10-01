from pygears import gear


@gear
def data_dly(din, *, len) -> b'din':
    '''Delays data by len cycles. Implemented as #len dregs in series'''
    pass
