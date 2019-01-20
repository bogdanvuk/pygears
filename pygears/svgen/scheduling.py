import typing as pytypes
from dataclasses import dataclass, field

import hdl_types as ht

async_types = [ht.Yield]


def check_if_blocking(stmt):
    if type(stmt) in async_types:
        return stmt
    elif isinstance(stmt, ht.Block):
        return stmt
    else:
        return None


def find_hier_blocks(body):
    hier = []
    for stmt in body:
        b = check_if_blocking(stmt)
        if b:
            hier.append(b)
    return hier


@dataclass
class CBlock:
    parent: pytypes.Any
    child: list
    hdl_block: pytypes.Any
    state_ids: list = field(init=False, default=None)


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


class Scheduler(ht.TypeVisitor):
    def __init__(self):
        self.scope = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def non_state_block(self, block):
        return (isinstance(block, MutexCBlock)
                and (not find_hier_blocks(block.hdl_block.stmts)))

    def visit_block(self, cnode, body):
        self.enter_block(cnode)

        free_stmts = []
        leaf_found = None

        for stmt in body:
            child = self.visit(stmt)
            if (child is None) or self.non_state_block(child):
                if leaf_found:
                    leaf_found.hdl_blocks.append(stmt)
                else:
                    free_stmts.append(stmt)
            else:
                if leaf_found:
                    cnode.child.append(leaf_found)
                    assert len(free_stmts) == 0
                else:
                    if free_stmts:
                        if isinstance(child, Leaf):
                            child.hdl_blocks = free_stmts + child.hdl_blocks
                        else:
                            # safe guard
                            from .hdl_ast import VisitError
                            raise VisitError("Free stmts cannot be here..")

                leaf_found = child
                child = None

        if leaf_found:
            cnode.child.append(leaf_found)
        else:
            if (not cnode.child) and free_stmts:
                assert isinstance(cnode, MutexCBlock)
                cnode.child.append(
                    Leaf(parent=self.scope[-1], hdl_blocks=free_stmts))

        self.exit_block()

        return cnode

    def visit_Module(self, node):
        cblock = SeqCBlock(parent=None, hdl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IntfBlock(self, node):
        cblock = SeqCBlock(parent=self.scope[-1], hdl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IntfLoop(self, node):
        cblock = SeqCBlock(parent=self.scope[-1], hdl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IfBlock(self, node):
        cblock = MutexCBlock(parent=self.scope[-1], hdl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_ContainerBlock(self, node):
        cblock = MutexCBlock(parent=self.scope[-1], hdl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_Loop(self, node):
        hier = find_hier_blocks(node.stmts)
        if hier:
            cblock = SeqCBlock(parent=self.scope[-1], hdl_block=node, child=[])
            return self.visit_block(cblock, node.stmts)
        else:
            # safe guard
            from .hdl_ast import VisitError
            raise VisitError("If loop isn't blocking stmts should be merged")

    def visit_Yield(self, node):
        return Leaf(parent=self.scope[-1], hdl_blocks=[node])

    def visit_all_Expr(self, node):
        return None
