from pygears import gear


@gear(outnames=['dout', 'pred_out'])
def release_after_eot(din: 'w_din',
                      pred: 'w_pred') -> ('w_din', 'w_pred'):
    pass
