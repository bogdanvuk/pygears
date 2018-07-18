from pygears import gear


@gear
def data_dly(din: 'w_din', *, len) -> b'w_din':
    '''Delays data by len cycles. Implemented as #len dregs in series'''
    pass
