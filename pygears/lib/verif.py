import inspect
from pygears import GearDone, gear
from pygears.lib import decoupler
from pygears.util.utils import quiter
from pygears.typing import Uint
from pygears.typing import Any
from pygears.sim import sim_assert, sim_log
from pygears.typing import Queue, typeof


class TypingYieldVisitorBase:
    def visit(self, data, dtype):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)
        ret = visit_func(data, dtype)
        if inspect.isgenerator(ret):
            yield from ret
        else:
            yield ret

    def visit_default(self, data, dtype):
        yield data


class TypeDrvVisitor(TypingYieldVisitorBase):
    def visit_queue(self, data, dtype):
        for (i, d), eot in quiter(enumerate(data)):
            for ret in self.visit(d, dtype.sub()):
                if dtype.lvl == 1:
                    yield (ret, Uint[1](eot))
                else:
                    yield (ret[0], Uint[ret[1].width + 1](ret[1]) +
                           (eot << ret[1].width))


def typeseq(t, v):
    if type(v) == t:
        yield v
    else:
        for d in TypeDrvVisitor().visit(v, t):
            try:
                yield t(d)
            except TypeError:
                sim_log().error(
                    f'Cannot convert value "{d}" to type "{repr(t)}"')


@gear
async def drv(*, t, seq) -> b't':
    """Outputs one data at the time from the iterable ``seq`` cast to the type
    ``t``.

    Args:
        t: Type of the data to output
        seq: An iterable generating data to be output

    Returns:
        Data of the type ``t``

    >>> drv(t=Uint[8], seq=range(10))

    If ``t`` is a :class:`Queue` type of certain level, then ``seq`` should
    generate nested iterables of the same level::

        q1 = ((11, 12), (21, 22, 23))
        q2 = ((11, 12, 13))

    >>> drv(t=Queue[Uint[8], 2], seq=[q1, q2])
    """

    for s in seq:
        for val in typeseq(t, s):
            yield val

    raise GearDone


@gear
async def secdrv(seqin, *, t) -> b't':
    async with seqin as seq:
        for val in seq:
            if type(val) == t:
                yield val
            else:
                for d in TypeDrvVisitor().visit(val, t):
                    yield t(d)


class Partial:
    def __new__(cls, val):
        if isinstance(val, Partial):
            return val
        else:
            obj = super().__new__(cls)
            obj.__init__(val)
            return obj

    def __init__(self, val):
        self._val = val

    @property
    def val(self):
        return self._val


class TypeMonitorVisitor:
    def __init__(self, dtype):
        self.data = None
        self.dtype = dtype

    def __bool__(self):
        return isinstance(self.data, Partial)

    def append(self, elem):
        self.data = self.visit(self.data, elem, self.dtype)
        return self.data

    def visit(self, data, elem, dtype):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)

        return visit_func(data, elem, dtype)

    def visit_default(self, data, elem, dtype):
        return elem

    def visit_queue(self, data, elem, dtype):
        if dtype.lvl == 1:
            sub_elem = elem[0]
        else:
            sub_elem = elem.sub()

        if not data:
            sub_data = None
            data = []
        else:
            data = data.val
            if isinstance(data[-1], Partial):
                sub_data = data.pop()
            else:
                sub_data = None

        sub_data = self.visit(sub_data, sub_elem, dtype.sub())
        data.append(sub_data)

        eot = all(elem.eot)
        if eot and (not isinstance(sub_data, Partial)):
            return data
        else:
            return Partial(data)


@gear
async def mon(din, *, t=b'din') -> Any:
    v = TypeMonitorVisitor(t)
    data = None
    while (isinstance(data, Partial) or data is None):
        # print('Monitor waiting')
        item = await din.get()
        # print('Monitor got: ', item)
        data = v.visit(data, item, t)

    # print('Monitor emits: ', data)
    yield data


def match_check(data, ref, tolerance):
    low = ref - tolerance
    high = ref + tolerance
    return low <= data <= high


def tolerance_check(items, tolerance):
    match = False

    if typeof(type(items[0]), Queue):
        for val in items:
            match = match_check(val.data, items[0].data, tolerance)
            if match:
                match = val.eot == items[0].eot

            if not match:
                break
    else:
        for val in items:
            match = match_check(val, items[0], tolerance)
            if not match:
                break

    return match


@gear
async def scoreboard(*din: b't', report, tolerance=0) -> None:
    """Generic scoreboard used from comparing actual results from the DUT to
    expected results. Eventual mismatches are asserted using the ``sim_assert``
    function meaning that any ``error`` behaviour is controled via the ``sim``
    logger ``error`` settings.

    Args:
        din: Outputs from both the DUT and ref. model. All intpus are a PyGears
          interface
        report: List to with comparison results are appended
        tolerance: Optional tolerance when comparing results. The DUT result must
          be in the (expected - tolerance, expected+tolerance) range

    Returns:
        None
    """
    cnt = 0
    match_cnt = 0
    try:
        while True:
            items = []
            for d in din:
                items.append(await d.get())

            if tolerance != 0:
                match = tolerance_check(items, tolerance)
            else:
                match = all(v == items[0] for v in items)

            report.append({'match': match, 'items': items})
            cnt += 1
            if match:
                match_cnt += 1
            sim_assert(match, f'mismatch on #{cnt}: {items[0]}, {items[1]}')

    except GearDone as e:
        sim_log().info(f'Number of matches = {match_cnt}/{cnt}')
        raise e


@gear
async def check(din, *, ref):
    """Checks equality of input data with expected.

    Args:
        ref: A list of expected values

    Returns:
        None

    If type ``din`` is a :class:`Queue` of certain level, then ``ref`` should
    generate nested iterables of the same level
    """
    iter_ref = iter(ref)
    ref_seq = iter(())

    try:
        items = []
        while True:
            data = await din.get()
            items.append(data)

            try:
                ref_item = next(ref_seq)
            except StopIteration:
                ref_seq = typeseq(din.dtype, next(iter_ref))
                ref_item = next(ref_seq)

            sim_assert(
                data == ref_item,
                f'mismatch in item {len(items)-1}. Got: {data}, expected: {ref_item}'
            )
    except GearDone:
        ref_empty = False
        try:
            next(ref_seq)
        except StopIteration:
            try:
                next(iter_ref)
            except StopIteration:
                ref_empty = True

        if not ref_empty:
            sim_assert(items == ref,
                       f'mismatch. Got: {items}, expected: {ref}')

    except (GearDone, StopIteration):
        sim_assert(items == ref, f'mismatch. Got: {items}, expected: {ref}')


def tlm_verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


def verif(*stim, f, ref, delays=None, tolerance=0):
    """Verification environment for comparing DUV results with reference model.
    The environment instantiates the DUV and reference model and drives the
    passed stimulus to both. The outpus are passed to the scoreboard which
    compares the results. Outputs are decoupled to ensure there is no connection
    between the DUV and the environment. Optional delays can be added to all
    input and output interfaces.

    Args:
        stim: Input stimulus
        f: Gear to be verified
        ref: Gear used as reference model
        delays: List of delays for all inputs and outputs
        tolerance: Tolerance window when performing equality checks

    Returns:
        A report dictionary with pass/fail statistics
    """

    res_tlm = stim | f
    ref_tlm = stim | ref

    if not isinstance(res_tlm, tuple):
        res_tlm = (res_tlm, )
        ref_tlm = (ref_tlm, )

    report = [[] for _ in range(len(res_tlm))]

    if delays is None:
        delays = (None, ) * len(res_tlm)

    assert len(ref_tlm) == len(res_tlm)
    assert len(delays) == len(res_tlm)

    for r, res_intf, ref_intf, d in zip(report, res_tlm, ref_tlm, delays):
        if d is not None:
            res_intf = res_intf | d

        res_intf = res_intf | decoupler(depth=0)
        ref_intf = ref_intf | decoupler(depth=0)

        scoreboard(res_intf, ref_intf, report=r, tolerance=tolerance)

    return report


def directed(*stim, f, ref, delays=None):
    """Similar to ``verif`` function, except ``ref`` is a list of expected results"""
    if stim:
        res = stim | f
    else:
        res = f

    if not isinstance(res, tuple):
        res = (res, )
        ref = (ref, )

    if delays is None:
        delays = (None, ) * len(res)

    assert len(ref) == len(res)
    assert len(delays) == len(res)

    for ref_inst, res_inst, delay_inst in zip(ref, res, delays):
        if delay_inst is not None:
            res_inst = res_inst | delay_inst
        res_inst | check(ref=ref_inst)


def directed_on_the_fly(*stim, f, refs, delays=None):
    """Similar to ``directed`` function, except ``ref`` is a generator and
    checking is done `on-the-fly`"""
    res_tlm = stim | f

    if not isinstance(res_tlm, tuple):
        res_tlm = (res_tlm, )

    if delays is None:
        delays = (None, ) * len(res_tlm)

    report = [[] for _ in range(len(res_tlm))]
    for r, res_intf, ref, d in zip(report, res_tlm, refs, delays):
        if d is not None:
            res_intf = res_intf | d

        res_intf = res_intf | decoupler(depth=0)
        # ref = ref | decoupler(depth=0)

        scoreboard(res_intf, ref, report=r)

    return report
