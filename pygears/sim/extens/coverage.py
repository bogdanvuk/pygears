import collections
import functools
import inspect
import itertools
from enum import IntEnum

from pygears.typing.visitor import TypingVisitorBase


class CoverBin:
    '''Holds count for specific value or values defined by enablement'''

    def __init__(self, name, threshold=None, enablement=lambda x: True):
        self.name = name
        self.threshold = threshold
        self.enablement = enablement
        self.cover_cnt = 0

    @property
    def hit(self):
        if self.threshold:
            return self.cover_cnt >= self.threshold
        else:
            return self.cover_cnt > 0

    def sample(self, val):
        if self.enablement(val):
            self.cover_cnt += 1

    def report(self):
        return f'bin {self.name}: {self.cover_cnt} (hit = {self.hit}, threshold = {self.threshold})'


class CoverPoint:
    '''Cover point for one type.
    Bins can be set as list of CoverBins or left as None
    '''

    def __init__(self,
                 name,
                 dtype=None,
                 bins=None,
                 threshold=None,
                 bind_field_name=None,
                 bind_dtype=False):
        self.name = name
        self.dtype = dtype
        self.bind_field_name = bind_field_name
        self.bind_dtype = bind_dtype
        if bins:
            self.bins = bins
            self.set_default_bin()
        else:
            self.bins = self.set_auto_bin()

        # set sub threshold only if not already set
        for b in self.bins:
            if not b.threshold:
                b.threshold = threshold

    def set_default_bin(self):
        '''Bin for holding all values which are not covered by other bins'''
        for i, b in enumerate(self.bins):
            if b.name == 'default':
                other = [
                    sub.enablement for j, sub in enumerate(self.bins) if j != i
                ]

                def default_enablement(val, other=other):
                    for func in other:
                        if func(val):
                            return False
                    return True

                b.enablement = default_enablement
                break

    def set_auto_bin(self):
        assert self.dtype, f'dtype must be set for CoverPoint if bins set as None'
        bins = []
        for i in range(2**len(self.dtype)):
            bins.append(
                CoverBin(
                    f'auto_bin{i}',
                    enablement=(lambda y: (lambda x: (y == x)))(i)))
        return bins

    def sample(self, val):
        for b in self.bins:
            b.sample(val)

    def report(self):
        report = f'Cover type {self.name}\n'
        report += f'Total hits: {self.cover_cnt}\n'
        report += f'Hit percent: {100 * self.hit / len(self.bins)}\n'
        for b in self.bins:
            report += f'\t{b.report()}\n'
        return report

    @property
    def cover_cnt(self):
        return sum([b.cover_cnt for b in self.bins])

    @property
    def hit(self):
        return sum([b.hit for b in self.bins])


class CoverageTypeVisitor(TypingVisitorBase):
    def __init__(self, name, cover_points):
        self.name = name
        self.cover_points = cover_points

    def sample(self, dtype, field, data):
        for cp in self.cover_points:
            if cp.bind_field_name:
                if cp.bind_field_name == field:
                    cp.sample(data)
            elif cp.bind_dtype:
                if cp.dtype == dtype:
                    cp.sample(data)
            elif not cp.bind_field_name and not cp.bind_dtype:
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
