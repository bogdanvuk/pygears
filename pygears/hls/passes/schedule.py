import attr
from copy import deepcopy
from ..ir_utils import res_true, HDLVisitor, ir, add_to_list, res_false, is_intf_id
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


@attr.s(auto_attribs=True)
class SchedStatus:
    forward_blocked: bool = False
    back_blocked: bool = False
    output_value: set = attr.Factory(set)
    cur_state: int = 0

    def copy(self):
        return deepcopy(self)


class Scheduler(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.scope = []
        self.path = []
        self.max_state = 0
        self.status = SchedStatus()

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def new_state(self):
        self.max_state += 1
        self.status = SchedStatus(cur_state=self.max_state)
        return self.max_state

    @property
    def parent(self):
        if self.scope:
            return self.scope[-1]
        else:
            return None

    def traverse_block(self, node):
        init_state = node.cur_state

        self.enter_block(node)

        for i, stmt in enumerate(node.stmts):
            self.visit(stmt)
            if not isinstance(stmt, ir.HDLBlock):
                if hasattr(stmt, 'state'):
                    node.cur_state = list(stmt.state)[0]
                else:
                    if node.cur_state == init_state:
                        stmt.state = node.state.copy()
                    else:
                        stmt.state = {node.cur_state}

                    if stmt.in_await == res_false:  # await clk()
                        node.cur_state = self.new_state()
                        stmt.state = {node.cur_state}
                    elif stmt.in_await != res_true:
                        self.status.forward_blocked = True
                        if self.status.back_blocked:
                            node.cur_state = self.new_state()
                            stmt.state = {node.cur_state}
                    elif stmt.exit_await != res_true:
                        self.status.back_blocked = True

            node.state.update(stmt.state)

        self.exit_block()

    def HDLBlock(self, node: ir.HDLBlock):
        if self.parent:
            node.cur_state = self.parent.cur_state
        else:
            node.cur_state = 0

        node.state = {node.cur_state}

        self.traverse_block(node)

    def AssignValue(self, node: ir.AssignValue):
        if is_intf_id(node.target):
            if node.target.name in self.status.output_value:
                node.state = {self.new_state()}

            self.status.output_value.add(node.target.name)

    def IfElseBlock(self, node):
        node.state = {self.parent.cur_state}
        node.cur_state = self.parent.cur_state

        init_state = self.status.copy()

        self.enter_block(node)

        out_states = []

        for stmt in node.stmts:
            self.status = init_state.copy()

            self.visit(stmt)

            out_states.append(self.status.copy())

            node.state.update(stmt.state)

        self.exit_block()


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
                    ir.AssignValue(
                        self.ctx.ref('state', ctx='store'),
                        ir.Await(ir.ResExpr(list(stmt.state)[0]),
                                 exit_await=res_false)))
                break

        if self.cur_state_id not in state:
            self.cur_state_id = list(state)[0]

        return stmts

    def ExprStatement(self, node: ir.ExprStatement):
        # TODO: Make this more general, now it convers the case of "await
        # clk()" like this
        if node.in_await != res_false:
            return node

    def HDLBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        in_cond = node.in_cond if self.cur_state else res_true
        exit_cond = node.exit_cond

        stmts = self.traverse_block(node.stmts, node.state)

        if in_cond == res_true and exit_cond == res_true:
            return stmts

        if in_cond == res_true and exit_cond == res_true and not stmts:
            return None

        return ir.HDLBlock(in_cond=in_cond, exit_cond=exit_cond, stmts=stmts)

    def LoopBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        block = ir.LoopBlock(
            in_cond=node.in_cond if self.cur_state else res_true,
            exit_cond=node.exit_cond,
            stmts=self.traverse_block(node.stmts, node.state))

        if 'state' in self.ctx.scope:
            if (self.cur_state and self.state_id != list(node.state)[0]):
                # and node.out_blocking):

                block.stmts.append(
                    ir.AssignValue(
                        self.ctx.ref('state', ctx='store'),
                        ir.Await(ir.ResExpr(list(node.state)[0]),
                                 exit_await=res_false)))
        return block

    def IfElseBlock(self, node):
        block = ir.IfElseBlock(stmts=[])

        for stmt in node.stmts:
            sub_stmts = self.visit(stmt)
            if isinstance(sub_stmts, list):
                if len(block.stmts) != 0:
                    # traverse_block logic stripped the HDLBlock from else
                    # path, we need it back
                    block.stmts.append(ir.HDLBlock(stmts=sub_stmts))
                else:
                    return sub_stmts
            else:
                add_to_list(block.stmts, sub_stmts)

        if len(block.stmts) == 1:
            return block.stmts[0]

        return block


def schedule(block, ctx):
    ctx.scope['rst_cond'] = ir.Variable('rst_cond', Bool)
    block.stmts.insert(
        0, ir.AssignValue(ctx.ref('rst_cond', 'store'), res_false))

    block.stmts.append(
        ir.AssignValue(ctx.ref('rst_cond', 'store'), res_true))

    Scheduler(ctx).visit(block)
    # print('*** Schedule ***')
    # print(PPrinter(ctx).visit(block))
    state_num = len(block.state)

    if state_num > 1:
        ctx.scope['state'] = ir.Variable(
            'state',
            val=ir.ResExpr(Uint[bitw(state_num - 1)](0)),
            reg=True,
        )

    stateblock = ir.IfElseBlock(stmts=[])
    for i in range(state_num):
        v = StateIsolator(ctx, i)
        res = v.visit(block)
        if isinstance(res, list):
            res = ir.HDLBlock(stmts=res)

        res.exit_cond = res_false

        stateblock.stmts.append(res)

        if state_num > 1:
            res.in_cond = ir.BinOpExpr((ctx.ref('state'), ir.ResExpr(i)),
                                       ir.opc.Eq)

    if state_num > 1:
        modblock = ir.CombBlock(stmts=[stateblock])
    else:
        modblock = ir.CombBlock(stmts=stateblock.stmts[0].stmts)

    modblock = infer_cycle_done(modblock, ctx)

    return modblock
