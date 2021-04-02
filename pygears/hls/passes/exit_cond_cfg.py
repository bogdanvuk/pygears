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


class ResolveBlocking(CfgDfs):
    def __init__(self):
        self.scopes = []

    @property
    def scope(self):
        return self.scopes[-1]

    def apply_await(self, node, blocking):
        if not node.next:
            return

        if blocking != ir.res_true and node.next:
            cond_wrap(node.next[0], self.scope.sink.prev[0], blocking)
            self.scope.blocking = ir.BinOpExpr((self.scope.blocking, blocking), ir.opc.And)

    def enter_BaseBlock(self, node):
        self.scopes.append(node)
        node.blocking = ir.res_true

    def exit_BaseBlock(self, node):
        self.scopes.pop()

    def exit_Await(self, node):
        if node.value.expr != 'forward':
            self.apply_await(node, node.value.expr)
        # Remove Await from cfg
        node.prev[0].next = node.next

    def exit_HDLBlock(self, block):
        blocking = ir.res_true
        for b in reversed(block.next):
            blocking = ir.ConditionalExpr((b.blocking, blocking), b.value.test)

        # TODO: Rest can be put in else statement if else has no blocking
        # statements. This might result in simpler code
        self.apply_await(block.sink, blocking)
