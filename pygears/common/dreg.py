from pygears import gear


@gear(svgen={'svmod_fn': 'dreg.sv'})
def dreg(din: 'tdin') -> b'tdin':
    pass
