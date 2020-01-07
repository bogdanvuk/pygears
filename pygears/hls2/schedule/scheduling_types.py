from dataclasses import dataclass, field
from typing import List, Union

from ..pydl import nodes


@dataclass
class CBlock:
    # TODO : newer versions of Python will not need the string
    parent: Union['CBlock', None]
    child: List[Union['CBlock', 'Leaf']]
    pydl_block: nodes.Block
    state_ids: List[int] = field(init=False, default=None)
    prolog: List[Union[nodes.Block, nodes.Expr]] = None
    epilog: List[Union[nodes.Block, nodes.Expr]] = None


@dataclass
class MutexCBlock(CBlock):
    pass


@dataclass
class SeqCBlock(CBlock):
    pass


@dataclass
class Leaf:
    parent: CBlock
    pydl_blocks: List[Union[nodes.Block, nodes.Expr]]
    state_id: int = None
