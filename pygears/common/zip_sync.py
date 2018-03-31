from pygears.core.gear import gear, hier


def op_tree(*din, gear, operands=2):
    outs = din
    while len(outs) >= operands:
        next_outs = []
        for i in range(0, len(outs), operands):
            if i <= len(outs) - operands:
                next_outs.append(gear(*outs[i:i + operands]))
            else:
                next_outs.extend(outs[i:i + operands])

        outs = tuple(next_outs)

    return outs


@hier
def zip_sync_vararg(*din):
    return op_tree(*din, gear=zip_sync)


@gear(alternatives=[zip_sync_vararg], enablement='len({din}) == 2')
def zip_sync(*din) -> '{din}':
    pass
