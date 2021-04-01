from ..cfg import CfgDfs, Node
from ..ir_utils import ir


def cond_wrap(first, last, test):
    source = first.prev
    sink = last.next

    if source[0] is last:
        return None

    cond_blk = Node(ir.HDLBlock(), prev=source)
    Node(ir.HDLBlockSink(), source=cond_blk, next_=sink)

    b_if = Node(ir.Branch(test=test), prev=[cond_blk], next_=[first])
    b_else = Node(ir.Branch(), prev=[cond_blk])
    cond_blk.next = [b_if, b_else]

    Node(ir.BranchSink(), source=b_if, prev=[last], next_=[cond_blk.sink])
    Node(ir.BranchSink(), source=b_else, prev=[b_else], next_=[cond_blk.sink])
    b_else.next = [b_else.sink]
    cond_blk.sink.prev = [b_else.sink, b_if.sink]

    first.prev = [b_if]
    last.next = [b_if.sink]
    source[0].next = [cond_blk]
    sink[0].prev = [cond_blk.sink]

    return cond_blk


class ExitAwaits(CfgDfs):
    def __init__(self):
        self.scopes = []
        self.in_awaited = set()

    @property
    def scope(self):
        return self.scopes[-1]

    def apply_await(self, node, exit_await):
        if not node.next:
            return

        if exit_await != ir.res_true and node.next:
            cond_wrap(node.next[0], self.scope.sink.prev[0], exit_await)
            self.scope.exit_await = ir.BinOpExpr((self.scope.exit_await, exit_await), ir.opc.And)

    def enter_BaseBlock(self, node):
        self.scopes.append(node)
        node.exit_await = ir.res_true
        if node.next and node.next[0] not in self.in_awaited:
            self.in_awaited.add(node.next[0])
            self.apply_await(node, node.next[0].value.in_await)

    def exit_BaseBlock(self, node):
        self.scopes.pop()

    def exit_Statement(self, node):
        self.apply_await(node, node.value.exit_await)

        if node.next and node.next[0] not in self.in_awaited:
            self.in_awaited.add(node.next[0])
            self.apply_await(node.next[0], node.next[0].value.in_await)

    def exit_HDLBlock(self, block):
        exit_await = ir.res_true
        for b in reversed(block.next):
            exit_await = ir.ConditionalExpr((b.exit_await, exit_await), b.value.test)

        self.apply_await(block.sink, exit_await)
