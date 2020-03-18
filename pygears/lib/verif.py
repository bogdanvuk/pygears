import inspect
import pprint
import textwrap

from pygears import GearDone, gear, datagear
from pygears.lib import decouple
from pygears.util.utils import quiter, gather
from pygears.typing import Uint
from pygears.typing import Any
from pygears.sim import sim_assert, sim_log, clk


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
        for d, eot in quiter(data):
            if type(d) == dtype:
                yield d
            else:
                for ret in self.visit(d, dtype.sub()):
                    if dtype.lvl == 1:
                        yield (ret, Uint[1](eot))
                    else:
                        yield (ret[0], eot @ ret[1])


def typeseq(t, v):
    if type(v) == t:
        yield v
    else:
        try:
            for d in TypeDrvVisitor().visit(v, t):
                try:
                    yield t(d)
                except (TypeError, ValueError):
                    sim_log().error(
                        f'Cannot convert value "{d}" to type "{repr(t)}"')
        except (TypeError, ValueError):
            sim_log().error(
                f'Cannot convert sequence "{v}" to the "{repr(t)}"')


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


@gear
async def scoreboard(*din: b't', report=None, cmp=None) -> None:
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
    def match_exact(x, y):
        return x == y

    if cmp is None:
        cmp = match_exact

    # print(f'Number of matches: -\r', end='')
    cnt = 0
    match_cnt = 0
    try:
        while True:
            items = []
            for d in din:
                items.append(await d.get())

            match = all(cmp(v, items[0]) for v in items)

            if report is not None:
                report.append({'match': match, 'items': items})

            cnt += 1
            if match:
                match_cnt += 1

            sim_assert(match, f'mismatch on #{cnt}: {items[0]}, {items[1]}')

            # print(f'Number of matches: {match_cnt:>4}/{cnt:>4}\r', end='')

    except GearDone as e:
        sim_log().info(f'Number of matches: {match_cnt:>4}/{cnt:>4}')
        raise e


@gear
async def check(din, *, ref, cmp=None):
    """Checks equality of input data with expected.

    Args:
        ref: A list of expected values

    Returns:
        None

    If type ``din`` is a :class:`Queue` of certain level, then ``ref`` should
    generate nested iterables of the same level
    """
    def match_exact(x, y):
        return x == y

    if cmp is None:
        cmp = match_exact

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
                cmp(data, ref_item),
                f'mismatch in item #{len(items)}. Got: {data}, expected: {ref_item}'
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
            sim_assert(
                items == ref,
                f"mismatch in number of items, got '{len(items)}' but expected '{len(ref)}'. "
                f"\ngot:\n{textwrap.indent(pprint.pformat(items), ' '*4)}"
                f"\nexp:\n{textwrap.indent(pprint.pformat(ref), ' '*4)}"
            )

    except (GearDone, StopIteration):
        sim_assert(
            items == ref,
            f"mismatch in number of items {len(items)} vs {len(ref)}. "
            f"\ngot:\n{textwrap.indent(pprint.pformat(items), ' '*4)}"
            f"\nexp:\n{textwrap.indent(pprint.pformat(ref), ' '*4)}"
        )


def tlm_verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


def verif(*stim, f, ref, delays=None, cmp=None, check_timing=False, make_report=False):
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

    if stim:
        res_tlm = stim | f
        ref_tlm = stim | ref
    else:
        res_tlm = f
        ref_tlm = ref

    if check_timing:
        ref_tlm, res_tlm = match_timing(ref_tlm, res_tlm)

    if not isinstance(res_tlm, tuple):
        res_tlm = (res_tlm, )
        ref_tlm = (ref_tlm, )

    if make_report:
        report = [[] for _ in range(len(res_tlm))]
    else:
        report = [None for _ in range(len(res_tlm))]

    if delays is None:
        delays = (None, ) * len(res_tlm)

    assert len(ref_tlm) == len(res_tlm)
    assert len(delays) == len(res_tlm)

    for r, res_intf, ref_intf, d in zip(report, res_tlm, ref_tlm, delays):
        if d is not None:
            res_intf = res_intf | d

        res_intf = res_intf | decouple(depth=0)
        ref_intf = ref_intf | decouple(depth=0)

        scoreboard(res_intf, ref_intf, report=r, cmp=cmp)

    return report


def directed(*stim, f, ref, delays=None, cmp=None):
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
        res_inst | check(ref=ref_inst, cmp=cmp)


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

        res_intf = res_intf | decouple(depth=0)
        # ref = ref | decouple(depth=0)

        scoreboard(res_intf, ref, report=r)

    return report


@gear
async def match_timing(*din) -> b'din':
    if any(not d.empty() for d in din):
        all_valid = all(not d.empty() for d in din)
        sim_assert(all_valid, f'not all inputs valid at the same time')

        async with gather(*din) as data:
            yield data

    await clk()


@datagear
def collect(val, *, result):
    result.append(val)
