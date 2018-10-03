from spike import Spike

with Spike('spike -d --isa=rv32i hello') as sp:
    print('A1 value before: ', hex(sp.reg(1)))
    sp.step()
    print('A1 value after:  ', hex(sp.reg(1)))
