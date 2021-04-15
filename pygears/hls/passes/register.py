from ..ir_utils import ir
from ..cfg import CfgDfs
from ..cfg_util import remove_node
from ..ir_utils import ir, IrRewriter, add_to_list, IrVisitor


class ResolveRegInits(IrRewriter):
    def __init__(self, ctx, scope_map=None):
        super().__init__()
        self.ctx = ctx

    def AssignValue(self, node: ir.AssignValue):
        if not isinstance(node.target, ir.Name):
            return node

        name = node.target.name

        if name not in self.ctx.reaching[id(node)]['in']:
            obj = self.ctx.scope[name]
            # If this is a register variable and assigned value is a literal value (ResExpr)
            if (isinstance(obj, ir.Variable) and obj.reg and isinstance(node.val, ir.ResExpr)
                    and node.val.val is not None):
                init_val = ir.CastExpr(node.val, obj.dtype)
                if obj.val is None:
                    node = ir.RegReset(obj)
                    obj.val = init_val
                    obj.any_init = False
                elif obj.val != init_val and obj.any_init:
                    breakpoint()
                    print('Hier?')

        return node


# class ResolveRegInits(CfgDfs):
#     def __init__(self, ctx):
#         self.ctx = ctx
#         super().__init__()

#     # TODO: How to detect registers used uninitialized?
#     def enter_AssignValue(self, node):
#         irnode: ir.AssignValue = node.value
#         if not isinstance(irnode.target, ir.Name):
#             return

#         breakpoint()
#         name = irnode.target.name

#         if name not in self.ctx.reaching[id(node.value)]['in']:
#             obj = self.ctx.scope[name]
#             # If this is a register variable and assigned value is a literal value (ResExpr)
#             if (isinstance(obj, ir.Variable) and obj.reg and isinstance(irnode.val, ir.ResExpr)
#                     and irnode.val.val is not None):
#                 init_val = ir.CastExpr(irnode.val, obj.dtype)
#                 if obj.val is None or obj.val == init_val:
#                     node.value = ir.RegReset(obj)
#                     obj.val = init_val
#                     obj.any_init = False
#                 elif obj.any_init:
#                     breakpoint()
#                     print('Hier?')


def infer_registers(modblock, ctx):
    return ResolveRegInits(ctx).visit(modblock)
