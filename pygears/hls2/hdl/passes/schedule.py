from .utils import res_true, HDLVisitor, nodes, pydl, nodes, add_to_list, res_false
from pygears.typing import bitw, Uint, Bool
from .loops import infer_cycle_done


class PPrinter(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.msg = ''
        self.indent = 0

    def enter_block(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        self.msg += f'{" "*self.indent}{line}\n'

    def HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block()

        return self.msg

    def generic_visit(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        return self.msg


class Scheduler(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.scope = []
        self.state = []
        self.path = []
        self.state_root = []
        self.stmt_states = {}
        self.max_state = 0

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def new_state(self):
        self.max_state += 1
        return self.max_state

    @property
    def parent(self):
        if self.scope:
            return self.scope[-1]
        else:
            return None

    def traverse_block(self, node):
        self.enter_block(node)

        for i, stmt in enumerate(node.stmts):
            self.visit(stmt)

            if stmt.out_blocking:
                node.cur_state = stmt.cur_state
                node.state.update(stmt.state)
                node.out_blocked = True

            if stmt.in_blocking:
                node.in_blocked = True

        if node.out_blocked:
            node.out_blocking = True

        if node.in_blocked:
            node.in_blocking = True

        self.exit_block()

    def HDLBlock(self, node: nodes.HDLBlock):
        node.out_blocking = False
        node.in_blocking = False
        node.out_blocked = False
        node.in_blocked = False

        if self.parent:
            node.cur_state = self.parent.cur_state
        else:
            node.cur_state = 0

        node.state = {node.cur_state}

        if self.parent and node.exit_cond != res_true:
            if self.parent.out_blocked:
                node.cur_state = self.new_state()
            else:
                node.cur_state = self.parent.cur_state

            node.state = {node.cur_state}
            node.out_blocking = True

        if node.in_cond != res_true:
            node.in_blocking = True

        self.traverse_block(node)

    def AssignValue(self, node):
        node.out_blocking = False
        node.in_blocking = False
        node.cur_state = self.parent.cur_state
        node.state = self.parent.state.copy()

    def IfElseBlock(self, node):
        node.state = {self.parent.cur_state}
        node.cur_state = self.parent.cur_state

        node.out_blocked = self.parent.out_blocked
        node.out_blocking = False
        node.in_blocking = False
        node.in_blocked = False

        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

            if stmt.out_blocking:
                node.state.update(stmt.state)
                node.out_blocking = True

            if stmt.in_blocking:
                node.in_blocking = True

        self.exit_block()

    def CombBlock(self, node):
        node.cur_state = 0
        node.state = {node.cur_state}

        node.out_blocked = False
        node.out_blocking = False
        node.in_blocked = False
        node.out_blocked = False

        self.traverse_block(node)

    def Await(self, node):
        node.out_blocking = True
        node.in_blocking = False
        if self.parent.out_blocked:
            node.cur_state = self.new_state()
        else:
            node.cur_state = self.parent.cur_state

        node.state = {node.cur_state}


class StateIsolator(HDLVisitor):
    def __init__(self, ctx, state_id):
        super().__init__(ctx)
        self.state_id = state_id
        self.cur_state_id = 0

    @property
    def cur_state(self):
        return self.cur_state_id == self.state_id

    def traverse_block(self, all_stmts, state):
        self.cur_state_id = list(state)[0]
        stmts = []

        for stmt in all_stmts:
            if self.state_id in stmt.state:
                if self.cur_state_id not in stmt.state:
                    self.cur_state_id = list(stmt.state)[0]

                add_to_list(stmts, self.visit(stmt))
            elif self.cur_state:
                stmts.append(
                    nodes.AssignValue(self.ctx.ref('state', ctx='store'),
                                      pydl.ResExpr(list(stmt.state)[0]),
                                      exit_cond=res_false))
                break

        if self.cur_state_id not in state:
            self.cur_state_id = list(state)[0]

        return stmts

    def HDLBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        in_cond = node.in_cond if self.cur_state else res_true
        opt_in_cond = node.opt_in_cond if self.cur_state else res_true
        exit_cond = node.exit_cond

        stmts = self.traverse_block(node.stmts, node.state)

        if in_cond == res_true and opt_in_cond == res_true and exit_cond == res_true:
            return stmts

        if in_cond == res_true and exit_cond == res_true and not stmts:
            return None

        return nodes.HDLBlock(in_cond=in_cond,
                              opt_in_cond=opt_in_cond,
                              exit_cond=exit_cond,
                              stmts=stmts)

    def LoopBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        block = nodes.LoopBlock(
            in_cond=node.in_cond if self.cur_state else res_true,
            opt_in_cond=node.opt_in_cond if self.cur_state else res_true,
            exit_cond=node.exit_cond,
            stmts=self.traverse_block(node.stmts, node.state))

        if 'state' in self.ctx.scope:
            if (self.cur_state and self.state_id != list(node.state)[0]
                    and node.out_blocking):
                block.stmts.append(
                    nodes.AssignValue(self.ctx.ref('state', ctx='store'),
                                      pydl.ResExpr(list(node.state)[0]),
                                      exit_cond=res_false))
        return block

    def IfElseBlock(self, node):
        block = nodes.IfElseBlock(stmts=[])

        for stmt in node.stmts:
            sub_stmts = self.visit(stmt)
            if isinstance(sub_stmts, list):
                if len(block.stmts) != 0:
                    breakpoint()

                return sub_stmts
            else:
                block.stmts.append(sub_stmts)

        if len(block.stmts) == 1:
            return block.stmts[0]

        return block


def schedule(pydl_ast, ctx):
    Scheduler(ctx).visit(pydl_ast)
    print(PPrinter(ctx).visit(pydl_ast))
    state_num = len(pydl_ast.state)

    if state_num > 1:
        ctx.scope['state'] = pydl.Variable(
            'state',
            val=pydl.ResExpr(Uint[bitw(state_num - 1)](0)),
            reg=True,
        )

    stateblock = nodes.IfElseBlock(stmts=[])
    for i in range(state_num):
        v = StateIsolator(ctx, i)
        res = v.visit(pydl_ast)
        if isinstance(res, list):
            res = nodes.HDLBlock(exit_cond=False, stmts=res)

        stateblock.stmts.append(res)

        if state_num > 1:
            res.opt_in_cond = pydl.BinOpExpr(
                (ctx.ref('state'), pydl.ResExpr(i)), pydl.opc.Eq)

    if state_num > 1:
        modblock = nodes.CombBlock(stmts=[stateblock])
    else:
        modblock = nodes.CombBlock(stmts=stateblock.stmts[0].stmts)

    modblock = infer_cycle_done(modblock, ctx)

    return modblock
