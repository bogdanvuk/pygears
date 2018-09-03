def bitw(num: int) -> int:
    accum, shifter = 0, 1
    while num >= shifter:
        shifter <<= 1
        accum += 1
    return accum


def ceil_pow2(num: int) -> int:
    return int(2**(bitw(num-1)))
