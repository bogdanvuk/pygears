from .conditions_utils import (ConditionsBase, find_cond_id, find_exit_cond,
                               nested_cycle_cond, nested_exit_cond,
                               nested_in_cond)
from .hls_blocks import ContainerBlock, Module
from .utils import state_expr


class ConditionsFinder(ConditionsBase):
    def __init__(self):
        self.scope = []

    def in_cond(self, hdl_block):
        cond = nested_in_cond(hdl_block)
        if cond is not None:
            self.add_in_cond(find_cond_id(cond))
        return cond

    def _create_state_cycle_cond(self, child):
        child_cond = nested_cycle_cond(child.hdl_block)
        self.add_cycle_cond(find_cond_id(child_cond))
        return state_expr(child.state_ids, child_cond)

    def _state_depend_cycle_cond(self, hdl_block):
        c_block = self.scope[-1]

        if c_block.prolog is not None and hdl_block in c_block.prolog:
            return self._create_state_cycle_cond(c_block.child[0])

        if c_block.epilog is not None and hdl_block in c_block.epilog:
            return self._create_state_cycle_cond(c_block.child[-1])

        for child_idx, child in enumerate(c_block.child):
            if (child.hdl_block == hdl_block) or (child.prolog is not None and
                                                  hdl_block in child.prolog):
                return self._create_state_cycle_cond(child)

            if child.epilog is not None and hdl_block in child.epilog:
                if len(c_block.child) > (child_idx + 1):
                    return self._create_state_cycle_cond(
                        c_block.child[child_idx + 1])

                return self._create_state_cycle_cond(child)

        raise Exception('State dependency but no child found in cycle cond')

    def cycle_cond(self, hdl_block):
        cond = []
        for i, c_block in enumerate(reversed(self.scope[1:])):
            # state changes break the cycle
            if len(c_block.state_ids) > len(self.scope[-1].state_ids):
                break

            if (i == 0) and c_block.hdl_block != hdl_block and len(
                    c_block.state_ids) > 1:
                return self._state_depend_cycle_cond(hdl_block)

            block = c_block.hdl_block
            if isinstance(block, ContainerBlock):
                continue

            if block.cycle_cond and block.cycle_cond != 1:
                cond.append(nested_cycle_cond(block))
                self.add_cycle_cond(find_cond_id(cond[-1]))

            if hasattr(block, 'multicycle') and block.multicycle:
                break

        cond = list(set(cond))
        return self.combine_conditions(cond)

    def _exit_cond(self, block):
        cond = nested_exit_cond(block)
        self.add_exit_cond(find_cond_id(cond))
        return cond

    def exit_cond(self, hdl_block):
        block = self.scope[-1].hdl_block
        return self._exit_cond(block)

    @property
    def rst_cond(self):
        if len(self.scope) == 1:
            assert isinstance(self.scope[0].hdl_block, Module)
            block = self.scope[0].hdl_block.stmts
        else:
            block = [s.hdl_block for s in self.scope[1:]]
        return find_exit_cond(block, search_in_cond=True)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def _find_cond(self, cond, **kwds):
        if cond is None:
            cond = 1

        if 'context_cond' in kwds:
            if cond == 1:
                return kwds['context_cond']

            cond = self.combine_conditions((cond, kwds['context_cond']), '&&')

        return cond

    def find_rst_cond(self, **kwds):
        cond = self.rst_cond
        return self._find_cond(cond, **kwds)

    def find_in_cond(self, hdl_block, **kwds):
        cond = self.in_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def find_cycle_cond(self, hdl_block, **kwds):
        cond = self.cycle_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def find_exit_cond(self, hdl_block, **kwds):
        cond = self.exit_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def find_exit_cond_by_scope(self, scope_id=-1):
        block = self.scope[scope_id].hdl_block
        return self._exit_cond(block)
