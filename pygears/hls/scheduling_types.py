from dataclasses import dataclass, field
from typing import List, Union

from .hls_expressions import Expr
from .pydl_types import Block


@dataclass
class CBlock:
    # TODO : newer versions of Python will not need the string
    parent: Union['CBlock', None]
    child: List[Union['CBlock', 'Leaf']]
    pydl_block: Block
    state_ids: List[int] = field(init=False, default=None)
    prolog: List[Union[Block, Expr]] = None
    epilog: List[Union[Block, Expr]] = None


@dataclass
class MutexCBlock(CBlock):
    pass


@dataclass
class SeqCBlock(CBlock):
    pass


@dataclass
class Leaf:
    parent: CBlock
    pydl_blocks: List[Union[Block, Expr]]
    state_id: int = None
