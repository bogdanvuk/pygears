from pygears.typing import bitw, typeof
from pygears.hls import ir
import hashlib
import inspect
import re

class Signed:
    pass

class ElemNotFound(Exception):
    pass

class VGenOffsetVisitor:
    def visit(self, type_, path):
        visit_func_name = f'visit_{type_.__name__}'

        if hasattr(self, visit_func_name):
            return getattr(self, visit_func_name)(type_, path)

        else:
            return self.visit_default(type_, path)

    def visit_Array(self, type_, path):
        if not path:
            return []

        key = path.pop(0)
        up = key.start
        assert key.stop is None

        elem = slice(f'({up})*{type_.data.width}', None, type_.data.width)

        # w = f"{bitw(type_.width-1)}'h{hex(type_.data.width)[2:]}"
        # elem = slice(f"{w}*({up})", None, w)
        return [(elem, type_.data)] + self.visit(type_.data, path)

    def visit_default(self, type_, path):
        if not path or type_.width == 1 :
            return []

        if isinstance(path[0], slice):
            return [(path[0], None)]

        if len(getattr(type_, 'fields', [])) > 1:
            key = path.pop(0)
            offset = 0
            for t, f in zip(type_, type_.fields):
                if f == key:
                    return [(slice(t.width+offset-1, offset), t)] + self.visit(t, path)
                offset += t.width
            else:
                raise ElemNotFound

        return []

class VGenTypeVisitor:
    def __init__(self):
        self.keys = []
        self.offset = 0

    def visit(self, type_):
        for c in inspect.getmro(type_.__class__):
            visit_func_name = f'visit_{c.__name__}'

            if hasattr(self, visit_func_name):
                yield from getattr(self, visit_func_name)(type_)

        else:
            yield from self.visit_default(type_)

    def visit_Array(self, type_):
        pass

    def visit_default(self, type_):
        base_offset = self.offset
        if len(getattr(type_, 'fields', [])) > 1:
            cur_offset = base_offset
            for t, f in zip(type_, type_.fields):
                self.keys.append(f)
                yield from self.visit(t)
                self.keys.pop()
                cur_offset += t.width
                self.offset = cur_offset

        yield self.keys, base_offset, type_

def paren_matcher (n):
    res = r"[^\[\]]*?(?:\["*n+r"[^\[\]]*?"+r"\][^\[\]]*?)*?"*n
    return res[9:-2]

SLICED_ID = re.compile(r'\b(\w+)\b(?:' + paren_matcher(2) + r'|(?:\.\w+\b))+(\s*<?=)?')

def split_id(s):
    path = []
    cur = ''
    par = 0
    rng = []
    for c in s:
        if c == '[':
            if par == 0:
                if cur: path.append(cur)
                cur = ''
                rng = []
            else:
                cur += c

            par += 1
        elif c == ']':
            par -= 1
            if par == 0:
                if cur:
                    rng.append(cur)
                    path.append(rng)
                cur = ''
            else:
                cur += c

        elif c == ':' and par == 1:
            rng.append(cur)
            cur = ''
        elif c == '.':
            if par == 0:
                if cur: path.append(cur)
                cur = ''
            else:
                cur += c
        else:
            cur += c

    if cur: path.append(cur)

    return path

def wire_name(path):
    return hashlib.sha1(path.encode()).hexdigest()[:8]

def combine_ranges(a, b):
    def is_step(x):
        return x.stop is None and x.step is not None

    def is_rng(x):
        return x.stop is not None and x.step is None

    def is_index(x):
        return x.stop is None and x.step is None

    def sl_arith(x):
        try:
            return str(eval(x))
        except:
            return x

    if is_rng(a) and is_rng(b):
        return slice(sl_arith(f'{a.stop} + {b.start}'), sl_arith(f'{a.stop} + {b.stop}'))
    elif is_rng(a) and is_step(b):
        return slice(sl_arith(f'{a.stop} + {b.start}'), None, b.step)
    elif is_rng(a) and is_index(b):
        return slice(sl_arith(f'{a.stop} + {b.start}'), None)
    elif is_step(a) and is_rng(b):
        return slice(sl_arith(f'{a.start} + {b.stop}'), None, sl_arith(f'{b.start} - {b.stop} + 1'))
    elif is_step(a) and is_step(b):
        return slice(sl_arith(f'{a.start} + {b.stop}'), None, b.step)
    elif is_step(a) and is_index(b):
        return slice(sl_arith(f'{a.start} + {b.start}'), None)
    else:
        return a


def rewrite(module, index):
    def substitute(m):
        name = m.group(1)
        lval = m.group(2)
        if lval is None:
            lval = ''

        if name not in index:
            return m.group(0)

        hit = m.group(0)
        if lval:
            hit = hit[:-len(lval)]

        path = []
        for i, p in enumerate(split_id(hit)):
            if i == 0:
                continue

            if isinstance(p, list):
                up = SLICED_ID.sub(substitute, p[0])
                down = None
                if len(p) > 1:
                    down = SLICED_ID.sub(substitute, p[1])

                path.append(slice(up, down))
            else:
                path.append(p)

        dtype = index[name]
        if typeof(dtype, ir.IntfType):
            if path[0] in ['valid', 'ready', 'data']:
                name = name + '_' + path[0]
                spath = [(p, None) for p in path[1:]]
            else:
                print(module)
                print(m.group(0))
                print(name)
                print(index)
                breakpoint()
                raise Exception

        else:
            try:
                spath = VGenOffsetVisitor().visit(dtype, path)
            except ElemNotFound:
                return m.group(0)

        s = name
        if spath:
            rng, dtype = spath[0]
            for p, dtype in spath[1:]:
                rng = combine_ranges(rng, p)

            if rng.start is None:
                breakpoint()

            if rng.stop is not None:
                s += f'[{rng.start}:{rng.stop}]'
            elif rng.step is not None:
                s += f'[{rng.start}+:{rng.step}]'
            else:
                s += f'[{rng.start}]'

            if getattr(dtype, 'signed', False) and not lval:
                s = f'$signed({s})'

        return s+lval

    module = SLICED_ID.sub(substitute, module)

    pat = re.compile(r'always_ff @\(posedge (\w+)\)')
    module = pat.sub(lambda m: f'always @(posedge {m.group(1)})', module)

    pat = re.compile(r'always_comb')
    module = pat.sub(lambda m: 'always @*', module)

    return module

# from pygears.typing import Tuple, Uint
# ret = rewrite('din_s.a = ~din.valid+din_s.b[0]-din_s.c[0:0]+din_s.ba', {'din': Intf(Tuple['a': Uint[2], 'b': Uint[3], 'c': Uint[1]])})
# print(ret)

# from pygears.typing import Queue, Uint
# ret = rewrite('eot_reg <= d.eot', {'d': Queue[Uint[2]]})
# print(ret)

# from pygears.typing import Tuple, Uint, Array, Int
# intfs = {
#     'din_s':
#     Tuple['a':Array[Uint[2], 4], 'b':Array[Tuple['c':Int[3], 'd':Uint[4]], 2]]
# }

# ret = rewrite('din_s.b[i] = din_s.b[2].d-din_s.b[0].c[1:0]', intfs)

# print(ret)
# breakpoint()
# print(ret[1])
# print(ret[0])

# print(split_id('din_s[qrange_stop_dout_s.data[2:1]:0]'))

# from pygears.typing import Tuple, Uint, Array, Int, Queue
# intfs = {'din': Intf(Array[Uint[16], 4]),
#          'din_s': Array[Uint[16], 4],
#          'qrange_stop_dout': Intf(Queue[Uint[3], 1]),
#          'qrange_stop_dout_s': Queue[Uint[3], 1]}


# ret = rewrite('din_s[qrange_stop_dout_s.data[2]]', intfs)
# ret = rewrite('qrange_stop_dout_s.data[2:1]', intfs)
# print(paren_matcher(2))
# import parser

# pat = re.compile(r'(?:\[[^\[\]]*?(?:\[[^\[\]]*?\][^\[\]]*?)*?\][^\[\]]*?)')
# pat = re.compile(paren_matcher(2))
# # res = pat.findall('din_s(qrange_stop_dout_s.data(2:1):0)')
# print(paren_matcher(2))
# res = pat.findall('din_s[qrange_stop_dout_s.data[2:1]:0]')
# print(res)
# ret = parser.expr('din_s[qrange_stop_dout_s.data[2:1]:0]')
# breakpoint()
