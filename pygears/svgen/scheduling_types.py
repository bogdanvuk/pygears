import typing as pytypes
from dataclasses import dataclass, field


@dataclass
class CBlock:
    parent: pytypes.Any
    child: list
    hdl_block: pytypes.Any
    state_ids: list = field(init=False, default=None)
    prolog: list = None
    epilog: list = None


@dataclass
class MutexCBlock(CBlock):
    pass


@dataclass
class SeqCBlock(CBlock):
    pass


@dataclass
class Leaf:
    parent: pytypes.Any
    hdl_blocks: pytypes.Any
    state_id: pytypes.Any = None
