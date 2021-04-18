from ..cfg import CfgDfs, Node
from ..ir_utils import ir
from ..cfg_util import remove_node


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

    i = source[0].next.index(first)
    source[0].next[i] = cond_blk
    sink[0].prev = [cond_blk.sink]

    return cond_blk


# TODO: Remove scoping, it is implemented in CfgDfs
class ResolveBlocking(CfgDfs):
    def __init__(self, ctx):
        self.scopes = []
        self.ctx = ctx

    @property
    def scope(self):
        return self.scopes[-1]

    def apply_await(self, node, blocking):
        if blocking == ir.res_true or not node.next:
            return

        cond_wrap(node.next[0], self.scope.sink.prev[0], blocking)
        self.scope.blocking = ir.BinOpExpr((self.scope.blocking, blocking), ir.opc.And)

    def enter_BaseBlock(self, node):
        self.scopes.append(node)
        node.blocking = ir.res_true
        node.break_ = ir.res_true

    def exit_BaseBlock(self, node):
        self.scopes.pop()
        self.apply_await(node.sink, node.blocking)

    def exit_LoopBody(self, node):
        self.scopes.pop()
        if node.break_ != ir.res_true:
            node.blocking = ir.BinOpExpr([ir.UnaryOpExpr(node.break_, ir.opc.Not), node.blocking],
                                         ir.opc.Or)

        self.apply_await(node.sink, node.blocking)

    def exit_Branch(self, node):
        self.scopes.pop()

    def exit_Await(self, node):
        if node.value.expr not in ['forward', 'back', 'break']:
            self.apply_await(node, node.value.expr)

        remove_node(node)

    def enter_Jump(self, stmt):
        irnode: ir.Jump = stmt.value
        if irnode.label == 'state':
            stmt.value = ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(irnode.where))
            self.apply_await(stmt, ir.res_false)
        elif irnode.label == 'break':
            self.apply_await(stmt, ir.res_false)
            self.scope.break_ = ir.res_false
            # self.scope.break_ = ir.BinOpExpr((self.scope.break_, self.scope.blocking), ir.opc.And)
            remove_node(stmt)
        else:
            remove_node(stmt)

    def exit_HDLBlock(self, block):
        blocking = ir.res_true
        for b in reversed(block.next):
            blocking = ir.ConditionalExpr((b.blocking, blocking), b.value.test)

        break_ = ir.res_true
        for b in reversed(block.next):
            break_ = ir.ConditionalExpr((b.break_, break_), b.value.test)

        self.scope.break_ = ir.BinOpExpr((self.scope.break_, break_), ir.opc.And)

        # TODO: Rest can be put in else statement if else has no blocking
        # statements. This might result in simpler code
        self.apply_await(block.sink, blocking)
