import collections
import functools
import inspect
import itertools
import pickle
import time
import os
from enum import IntEnum

from pygears.core.port import HDLProducer
from pygears.typing import Integer, Uint
from pygears.lib.verif import TypeMonitorVisitor, Partial
from pygears.util.utils import quiter


class CoverError(Exception):
    pass


class CoverBin:
    '''Holds count for specific value or values defined by enablement'''

    def __init__(self, name, threshold=None, enablement=lambda x: True):
        self.name = name
        self.threshold = threshold
        self.enablement = enablement
        self.cover_cnt = 0

    def sample(self, val):
        if self.enablement(val):
            self.cover_cnt += 1

    @property
    def covered(self):
        if self.threshold:
            return self.cover_cnt >= self.threshold
        else:
            return self.cover_cnt > 0

    @property
    def hit_percent(self):
        if self.covered:
            return 100
        else:
            if self.threshold:
                return 100 * (self.cover_cnt) / self.threshold
            else:
                return 0


class CoverPoint:
    '''Cover point for one type.
    Bins can be set as list of CoverBins or left as None
    '''

    def __init__(self,
                 name,
                 dtype=None,
                 bins=None,
                 ignore_bins=None,
                 threshold=None,
                 bind_field_name=None,
                 bind_dtype=False,
                 auto_bin_max=64):
        self.name = name
        self.dtype = dtype
        self.bind_field_name = bind_field_name
        self.bind_dtype = bind_dtype
        self.auto_bin_max = auto_bin_max
        self.ignore_bins = ignore_bins if ignore_bins else []
        self.threshold = threshold
        if bins:
            self.bins = bins
            self.set_default_bin()
        else:
            self.bins = self.set_auto_bin()

        # set sub threshold only if not already set
        for b in self.bins:
            if not b.threshold:
                b.threshold = self.threshold

    def set_default_bin(self):
        '''Bin for holding all values which are not covered by other bins'''
        for i, b in enumerate(self.bins):
            if b.name == 'default':
                other = [
                    sub.enablement for j, sub in enumerate(self.bins) if j != i
                ]
                other.extend([
                    sub.enablement for j, sub in enumerate(self.ignore_bins)
                    if j != i
                ])

                def default_enablement(val, other=other):
                    for func in other:
                        if func(val):
                            return False
                    return True

                b.enablement = default_enablement
                break

    def set_auto_bin(self):
        '''Creates automatic (explicit) bins
        The number of bins created is set by auto_bin_max and
        the enablement is if a value bellongs to the bin range
        '''
        if not self.dtype:
            raise CoverError(
                f'dtype must be set for CoverPoint if bins set as None')
        if not issubclass(self.dtype, Integer):
            raise CoverError(
                f'Automatic (implicit) bins only supported for integers')
        if self.ignore_bins:
            raise CoverError(
                'Automatic bins do not support ignore bins for now')

        bins = []
        if self.auto_bin_max < 2**len(self.dtype):
            bin_num = self.auto_bin_max
            bin_rng = 2**len(self.dtype) // self.auto_bin_max
        else:
            bin_num = 2**len(self.dtype)
            bin_rng = 1

        for i in range(bin_num):
            bins.append(
                CoverBin(
                    f'auto_bin{i}',
                    enablement=
                    (lambda y: (lambda x: (x in range(y * bin_rng, (y + 1) * bin_rng)))
                     )(i)))
        return bins

    def sample(self, val):
        for b in self.bins:
            b.sample(val)

    @property
    def cover_cnt(self):
        return sum([b.cover_cnt for b in self.bins])

    @property
    def covered(self):
        return all([b.covered for b in self.bins])

    @property
    def hit_percent(self):
        return 100 * sum([b.covered for b in self.bins]) / len(self.bins)


class CoverageTypeVisitor:
    def __init__(self, cover_points):
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

    def set_field_prefix(self, field):
        if field:
            return field + '.'
        else:
            return ''

    def visit(self, dtype, field=None, data=None):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)
        ret = visit_func(dtype, field, data)
        if inspect.isgenerator(ret):
            yield from ret
        else:
            yield ret

    def visit_default(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        yield data

    def visit_union(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        field = self.set_field_prefix(field)
        for _ in self.visit(dtype[0], f'{field}data', data=data.data):
            pass
        for _ in self.visit(dtype[-1], f'{field}ctrl', data=data.ctrl):
            pass
        yield data

    def visit_queue(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        field = self.set_field_prefix(field)
        for (i, d), eot in quiter(enumerate(data)):
            for ret in self.visit(dtype.sub(), f'{field}data', data=d):
                if dtype.lvl == 1:
                    self.sample(Uint[1], 'eot', data=eot)
                    yield (ret, Uint[1](eot))
                else:
                    self.sample(
                        dtype.eot,
                        'eot',
                        data=(int(ret[1]) + (eot << ret[1].width)))
                    yield (
                        ret[0],
                        Uint[ret[1].width + 1](ret[1]) + (eot << ret[1].width))

    def visit_tuple(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        field_p = self.set_field_prefix(field)
        for i, d in enumerate(data):
            if hasattr(dtype, '__parameters__'):
                field = field_p + dtype.__parameters__[i]
            else:
                field = field_p + f'f{i}'
            t = dtype[i]
            for _ in self.visit(t, field, data=d):
                pass
        yield data

    def visit_array(self, dtype, field=None, data=None):
        self.sample(dtype, field, data)
        field = self.set_field_prefix(field)
        for i, d in enumerate(data):
            for _ in self.visit(dtype[i], f'{field}f{i}', data=d):
                pass
        yield data


class CoverGroup:
    '''Group holds all cover points for one variable
    and calls the visitor for sampling'''

    def __init__(self, name, dtype, cover_points=None):
        self.name = name
        self.dtype = dtype
        self.cover_points = cover_points

    def sample(self, val):
        for _ in CoverageTypeVisitor(cover_points=self.cover_points).visit(
                self.dtype, data=val):
            pass

    def report(self):
        r = '=' * 80 + '\n'
        r += f'Coverge report for group {self.name}\n'
        r += '=' * 80 + '\n'
        for p in self.cover_points:
            r += f'Cover point: {p.name}'
            r += f' ({p.hit_percent:.2f}%, cover_cnt: {p.cover_cnt}, threshold: {p.threshold})\n'
            r += 'Bins\n'
            for b in p.bins:
                r += f'\t{b.name}: {b.hit_percent:.2f}%, cover_cnt: {b.cover_cnt}, threshold: {b.threshold}\n'
            r += '-' * 80 + '\n'
        r += '=' * 80 + '\n'
        return r


class CoverSingleValue:
    '''Coverage of single unpacked values. Combine before sampling'''

    def __init__(self, cg=None, en=True):
        self.cg = cg
        self.en = en
        self.data = None
        self.v = TypeMonitorVisitor(self.cg.dtype)

    def sample(self, item):
        self.data = self.v.visit(self.data, item, self.cg.dtype)
        if not (isinstance(self.data, Partial) or self.data is None):
            if self.en:
                self.cg.sample(self.data)
            self.data = None


class CoverIterator(collections.abc.Iterator):
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


class CoverBase:
    def __init__(self, cg=None, en=True):
        self.cg = cg
        self.en = en
        self.cover_single = None

    def sample(self, val):
        if self.en:
            if inspect.isgenerator(val):
                return CoverIterator(it=val, cg=self.cg, en=self.en)
            else:
                if not self.cover_single:
                    self.cover_single = CoverSingleValue(
                        cg=self.cg, en=self.en)
                self.cover_single.sample(val)
        return val


class CoverFunction(CoverBase):
    '''Wrapper around functions that need to be covered'''

    def __init__(self,
                 func,
                 cg=None,
                 en=True,
                 sample_type=FuncSampleType.result):
        super(CoverFunction, self).__init__(cg, en)
        functools.update_wrapper(self, func)
        self.func = func
        self.sample_type = sample_type

    def __call__(self, *arg, **kw):
        result = self.func(*arg, **kw)
        if self.sample_type == FuncSampleType.result:
            result = self.sample(result)
        else:
            self.sample(*arg, **kw)
        return result


def cover_func(cg, en=True, sample_type=FuncSampleType.result):
    '''Decorator for functions that need to be covered'''

    def cover(func):
        return CoverFunction(func=func, cg=cg, en=en, sample_type=sample_type)

    return cover


class CoverIntf(CoverBase):
    def __init__(self, intf, cg=None, en=True):
        super(CoverIntf, self).__init__(cg, en)
        self.intf = intf

    def event(self, intf, val):
        if intf is self.intf:
            self.sample(val)
        return True


def cover_intf(intf, cg, en=True):
    '''Function to register which interface needs to be covered'''
    while not isinstance(intf.producer, HDLProducer) and intf.producer:
        intf = intf.producer

    c = CoverIntf(intf, cg=cg, en=en)
    intf.events['put'].append(c.event)


def save_coverage(cg, outdir):
    timestr = time.strftime('%Y%m%d_%H%M%S')
    del cg.dtype
    for i in range(len(cg.cover_points)):
        del cg.cover_points[i].dtype
        for j in range(len(cg.cover_points[i].bins)):
            del cg.cover_points[i].bins[j].enablement
    path = os.path.join(outdir, f'{cg.name}_{timestr}.p')
    pickle.dump(cg, open(path, 'wb'))


def merge_cover_groups(cg0, cg1):
    cg = cg0
    for cp_idx, cp in enumerate(cg.cover_points):
        for bin_idx in range(len(cp.bins)):
            cg.cover_points[cp_idx].bins[
                bin_idx].cover_cnt += cg1.cover_points[cp_idx].bins[
                    bin_idx].cover_cnt
    return cg


def merge_coverage(name, outdir):
    merged_cg = None
    for fn in os.listdir(outdir):
        if name in fn:
            curr_cg = pickle.load(open(os.path.join(outdir, fn), 'rb'))
            if merged_cg:
                merged_cg = merge_cover_groups(merged_cg, curr_cg)
            else:
                merged_cg = curr_cg
    return merged_cg
