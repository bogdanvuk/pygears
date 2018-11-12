import collections
import functools
import inspect
import itertools
from enum import IntEnum

from pygears.typing.visitor import TypingVisitorBase


class CoverBin:
    '''Holds count for specific value or values defined by enablement'''

    def __init__(self, name, enablement=lambda x: True):
        self.name = name
        self.enablement = enablement
        self.cover_cnt = 0

    def sample(self, val):
        if self.enablement(val):
            self.cover_cnt += 1

    def report(self):
        return f'bin {self.name}: {self.cover_cnt}'


class CoverBinSeen:
    '''Holds count every value seen'''

    def __init__(self, name):
        self.name = name
        self.cover_cnt = 0
        self.cover_vals = {}

    def sample(self, val):
        self.cover_cnt += 1
        if val in self.cover_vals:
            self.cover_vals[val] += 1
        else:
            self.cover_vals[val] = 1

    def report(self):
        return f'bin {self.name}: {self.cover_vals}'


class CoverType:
    '''Cover by type.
    Bins can be set as list of CoverBins or CoverBinSeen.
    If left as None one auto_bin is created for all values.
    '''

    def __init__(self, name, bins=None):
        self.name = name
        if bins:
            self.set_default_bin(bins)
            self.bins = bins
        else:
            self.bins = [CoverBin('auto_bin')]

    def set_default_bin(self, bins):
        '''Bin for holding all values which are not covered by other bins'''
        for i, b in enumerate(bins):
            if b.name == 'default':
                other = [
                    sub.enablement for j, sub in enumerate(bins) if j != i
                ]

                def default_enablement(val, other=other):
                    for func in other:
                        if func(val):
                            return False
                    return True

                b.enablement = default_enablement
                break
        return bins

    def sample(self, val):
        for b in self.bins:
            b.sample(val)

    def report(self):
        report = f'Cover type {self.name}\n'
        report += f'Total hits: {sum([b.cover_cnt for b in self.bins])}\n'
        for b in self.bins:
            report += f'\t{b.report()}\n'
        return report


class CoverTypeBind(CoverType):
    def __init__(self, name, bins=None, bind_field_name=None, bind_dtype=None):
        super(CoverTypeBind, self).__init__(name, bins)
        self.bind_field_name = bind_field_name
        self.bind_dtype = bind_dtype


class CoverageTypeVisitor(TypingVisitorBase):
    def __init__(self, name, cover_points):
        self.name = name
        self.cover_points = cover_points

    def sample(self, dtype, field, data):
        for cp in self.cover_points:
            if cp.bind_field_name in [field, None
                                      ] and cp.bind_dtype in [dtype, None]:
                cp.sample(data)

    def visit_queue(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        for d in data:
            self.visit(dtype[0], 'data', data=d)

    def visit_tuple(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        for i, d in enumerate(data):
            if hasattr(dtype, '__parameters__'):
                field = dtype.__parameters__[i]
            else:
                field = f'f{i}'
            self.visit(dtype[i], field, data=d)

    def visit_uint(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)

    def report(self):
        r = ''
        for p in self.cover_points:
            r += f'{p.report()}\n'
        return r


class CoverGroup:
    '''Group holds all cover points for one variable
    and calls the visitor for sampling'''

    def __init__(self, name, dtype, cover_points=None):
        self.name = name
        self.dtype = dtype
        self.visitor = CoverageTypeVisitor(
            'coverage_visitor', cover_points=cover_points)

    def sample(self, val):
        self.visitor.visit(self.dtype, data=val)

    def report(self):
        report = '-' * 80
        report += f'\nCoverge report for group {self.name}\n'
        report += '-' * 80
        report += f'\n{self.visitor.report()}'
        report += '-' * 80
        return report


class CoverIterator(collections.Iterator):
    '''Coverage of iterators.
    Wraps around the iterator and copies the values'''

    def __init__(self, it, cg=None, en=True):
        self.it, self.nextit = itertools.tee(iter(it))
        self.cg = cg
        self.en = en
        self._advance()

    def _advance(self):
        try:
            self.lookahead = next(self.nextit)
            if self.en:
                self.cg.sample(self.lookahead)
        except StopIteration:
            pass

    def __next__(self):
        self._advance()
        return next(self.it)


class FuncSampleType(IntEnum):
    result = 0
    args = 1


class CoverFunction:
    '''Wrapper around functions that need to be covered'''

    def __init__(self,
                 func,
                 cg=None,
                 en=True,
                 sample_type=FuncSampleType.result):
        functools.update_wrapper(self, func)
        self.func = func
        self.cg = cg
        self.en = en
        self.sample_type = sample_type

    def __call__(self, *arg, **kw):
        result = self.func(*arg, **kw)
        if self.en:
            if self.sample_type == FuncSampleType.result:
                if inspect.isgenerator(result):
                    return CoverIterator(it=result, cg=self.cg, en=self.en)
                else:
                    self.cg.sample(result)
            else:
                self.cg.sample(*arg, **kw)
        return result


def cover_func(cg, en=True, sample_type=FuncSampleType.result):
    '''Decorator for functions that need to be covered'''

    def cover(func):
        return CoverFunction(func=func, cg=cg, en=en, sample_type=sample_type)

    return cover
