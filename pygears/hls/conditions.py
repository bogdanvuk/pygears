from .conditions_finder import ConditionsFinder
from .conditions_utils import ConditionsBase


class Conditions(ConditionsBase):
    def __init__(self):
        self.scope = []
        self.cond_finder = ConditionsFinder()

    def enter_block(self, block):
        self.scope.append(block)
        self.cond_finder.enter_block(block)

    def exit_block(self):
        self.cond_finder.exit_block()
        self.scope.pop()

    @property
    def rst_cond(self):
        return self.cond_finder.rst_cond

    def find_rst_cond(self, **kwds):
        cond = self.cond_finder.rst_cond
        return self._find_cond(cond, **kwds)

    def find_in_cond(self, hdl_block, **kwds):
        cond = self.cond_finder.in_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def find_cycle_cond(self, hdl_block, **kwds):
        cond = self.cond_finder.cycle_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def find_exit_cond(self, hdl_block, **kwds):
        cond = self.cond_finder.exit_cond(hdl_block)
        return self._find_cond(cond, **kwds)

    def _find_cond(self, cond, **kwds):
        if cond is None:
            cond = 1

        if 'context_cond' in kwds:
            if cond == 1:
                return kwds['context_cond']

            cond = self.combine_conditions((cond, kwds['context_cond']), '&&')

        return cond

    def find_exit_cond_by_scope(self, scope_id=-1):
        return self.cond_finder.exit_cond_by_scope(scope_id)
