import itertools
from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body
from pygears import registry
from pygears.hls2.pydl import nodes as pydl
from pygears.hls2.hdl import nodes
from pygears.hls2 import Context, GearContext, FuncContext, Scope
from pygears.typing import code, Bool
from pygears.core.port import Port
from dataclasses import dataclass, field
from typing import List
from pygears import Intf

from ..util import separate_conditions
from .sv_expression2 import svexpr
from .util import svgen_typedef

REG_TEMPLATE = """
always @(posedge clk) begin
    if(rst | rst_cond) begin
        {0} <= {1};
    end else if ({0}_en && cycle_done) begin
        {0} <= {0}_next;
    end
end
"""

res_true = pydl.ResExpr(Bool(True))


@dataclass
class BlockLines:
    header: List = field(default_factory=list)
    content: List = field(default_factory=list)
    footer: List = field(default_factory=list)


@dataclass
class IfElseBlock(BlockLines):
    pass


class SVCompiler(InstanceVisitor):
    def __init__(self, ctx, visit_var, writer, selected, aux_funcs=None):
        self.ctx = ctx
        self.writer = writer
        self.visit_var = visit_var
        self.selected = selected
        self.block_lines = []
        self.block_stack = []
        self.defaults = Scope()

        if aux_funcs is None:
            aux_funcs = {}

        self.aux_funcs = aux_funcs

    @property
    def cur_block_lines(self):
        return self.block_lines[-1]

    def trim_cur_block(self):
        content = []
        for c in self.cur_block_lines.content:
            if isinstance(c, BlockLines) and not c.content:
                continue

            content.append(c)

        self.cur_block_lines.content = content

    def prepend(self, line):
        self.cur_block_lines.content.insert(0, line)

    def write(self, line):
        self.cur_block_lines.content.append(line)

    def header(self, line):
        self.cur_block_lines.header.append(line)

    def footer(self, line):
        self.cur_block_lines.footer.append(line)

    def enter_block(self, block):
        self.defaults.subscope()
        self.block_stack.append(block)
        bl = BlockLines()
        self.block_lines.append(bl)

        if not isinstance(block, nodes.HDLBlock):
            return

        maybe_else = 'else ' if getattr(block, 'else_branch', False) else ''

        in_cond = pydl.BinOpExpr((block.in_cond, block.opt_in_cond),
                                 pydl.opc.And)

        if in_cond != res_true:
            in_cond_val = svexpr(in_cond, self.aux_funcs)

            self.header(f'{maybe_else}if ({in_cond_val}) begin')
        elif maybe_else:
            self.header(f'else begin')

    def exit_block(self, block=None):
        self.defaults.upscope()

        bl = self.block_lines.pop()

        self.write(bl)

        self.block_stack.pop()

    def handle_defaults(self, target, stmt):
        if target not in self.defaults:
            self.defaults.items[target] = stmt
        elif stmt != self.defaults[target]:
            self.defaults[target] = stmt
            self.write(stmt)

    def _assign_value(self, stmt):
        if isinstance(stmt.target, pydl.SubscriptExpr):
            target = stmt.target.val
        elif isinstance(stmt.target, pydl.Name):
            target = stmt.target
            if target.name == 'out_res':
                breakpoint()
        else:
            raise Exception

        if not self.selected(target):
            return

        val = stmt.val

        if isinstance(target.obj, pydl.Variable) and target.obj.reg:
            name = svexpr(target, self.aux_funcs)
            svstmt = f"{name}_next = {svexpr(val, self.aux_funcs)}"
            self.handle_defaults(name, svstmt)

            self.write(f"{name}_en = 1")
            return

        if isinstance(target.obj, pydl.Interface):
            name = svexpr(target, self.aux_funcs)
            if target.ctx == 'store':
                svstmt = f"{name}_s = {svexpr(val, self.aux_funcs)}"
                self.handle_defaults(name, svstmt)

                self.write(f"{name}.valid = 1")
            elif target.ctx == 'ready':
                self.write(f"{name}.ready = 1")

            return

        target = svexpr(stmt.target, self.aux_funcs)
        svstmt = f"{target} = {svexpr(val, self.aux_funcs)}"

        self.handle_defaults(target, svstmt)

    def visit_AssertValue(self, node):
        self.write(f'assert ({svexpr(node.val.test, self.aux_funcs)})')
        self.write(f'else $error("{node.val.msg}");')

    def visit_AssignValue(self, node):
        assign_stmt = self._assign_value(node)
        if assign_stmt is not None:
            self.write(f'{assign_stmt};')

    def visit_StateBlock(self, node):
        self.write('case (state)')
        self.write.indent += 4
        for i, child in enumerate(node.stmts):
            self.write(f'{i}: begin')
            self.write.indent += 4
            self.visit(child)
            self.write.indent -= 4
            self.write('end')

        self.write.indent -= 4
        self.write('endcase')

    def list_initials(self):
        for name, obj in self.ctx.scope.items():
            if isinstance(obj, pydl.Interface):
                if obj.direction == 'in':
                    if self.selected(self.ctx.ref(name, ctx='ready')):
                        self.prepend(f"{name}.ready = {name}.valid ? 0 : 1'bx")
                else:
                    if self.selected(self.ctx.ref(name, ctx='store')):
                        self.prepend(f"{name}.valid = 0")
                        # self.write(f"{name}_s = {obj.dtype.width}'(1'bx)")

            elif isinstance(obj, pydl.Variable) and obj.reg:
                target = self.ctx.ref(name, ctx='store')
                if self.selected(target):
                    # self.write(f"{name}_next = {obj.dtype.width}'(1'bx)")
                    # self.write(f"{name}_next = {name}")
                    self.prepend(f'{svexpr(target, self.aux_funcs)}_en = 0')

            elif isinstance(obj, pydl.Variable):
                pass
                # if self.selected(self.ctx.ref(name, ctx='store')):
                #     self.write(f"{name} = {obj.dtype.width}'(1'bx)")

    def visit_CombBlock(self, node):
        self.block_lines.append(BlockLines())

        self.header(f'// Comb block for: {self.visit_var}')
        self.header(f'always_comb begin')

        self.visit_HDLBlock(node)

        self.trim_cur_block()

        for target, svstmt in self.defaults.items.items():
            self.prepend(svstmt)

        if self.cur_block_lines.content:
            self.list_initials()

        self.footer('end')

    def visit_FuncReturn(self, node):
        self.write(
            f"{svexpr(node.func.name, self.aux_funcs)} = {svexpr(node.expr, self.aux_funcs)}"
        )

    def visit_FuncBlock(self, node):
        self.block_lines.append(BlockLines())

        self.header('')

        self.visit_HDLBlock(node)

        self.footer(f'endfunction')
        self.footer('')

    def visit_CombSeparateStmts(self, node):
        if node.stmts:
            self.write(f'// Comb statements for: {self.visit_var}')
            for stmt in node.stmts:
                assign_stmt = self._assign_value(stmt)
                if assign_stmt is not None:
                    self.write(f'assign {assign_stmt};')
            self.write('')

    def visit_LoopBlock(self, node):
        self.visit_HDLBlock(node)

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.write(f'{assign_stmt};')

        for stmt in node.stmts:
            self.visit(stmt)

        self.trim_cur_block()

        self.exit_block(node)

    def visit_IfElseBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.write(f'{assign_stmt};')

        for i, stmt in enumerate(node.stmts):
            if i > 0:
                stmt.else_branch = True

            self.visit(stmt)

        content = []
        for c in reversed(self.cur_block_lines.content):
            if not content and not c.content:
                continue

            content.insert(0, c)

        self.cur_block_lines.content = content

        self.exit_block(node)


gear_module_template = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.gear_module(module_name, intfs, comment, sigs) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_block(block, writer):
    for h in block.header:
        writer.line(h)

    if block.header:
        writer.indent += 4

    for c in block.content:
        if isinstance(c, str):
            writer.line(c + ';')
        else:
            write_block(c, writer)

    if block.header:
        writer.indent -= 4
        if block.footer and block.footer[0] == 'endfunction':
            writer.line('endfunction')
        else:
            writer.line('end')


def typedef_or_inline(writer, dtype, name):
    res = svgen_typedef(dtype, name)
    if "\n" not in res[:-1]:
        return res.partition(' ')[-1].rpartition(';')[0].rpartition(' ')[0]

    writer.block(res)
    return f'{name}_t'


def svcompile(hdl_stmts, writer, ctx, title, selected, aux_funcs=None):
    v = SVCompiler(ctx, title, writer, selected=selected, aux_funcs=aux_funcs)
    v.visit(hdl_stmts)

    if not v.block_lines[0].content:
        return

    write_block(v.block_lines[0], writer)
    writer.line()


def write_module(ctx: Context,
                 hdl,
                 writer,
                 subsvmods,
                 funcs,
                 template_env,
                 config=None):
    if config is None:
        config = {}

    aux_funcs = {}

    # svcompile(hdl, writer, ctx, "proba", selected=lambda x: x)

    for name, expr in ctx.regs.items():
        name = svexpr(ctx.ref(name))
        writer.line(f'logic {name}_en;')
        name_t = typedef_or_inline(writer, expr.dtype, name)
        writer.line(f'{name_t} {name}, {name}_next;')
        writer.line()

    for name, expr in ctx.intfs.items():
        if isinstance(expr.intf, Intf):
            writer.line(f'dti#({expr.dtype.width}) {name}();')

        name_t = typedef_or_inline(writer, expr.dtype, name)
        writer.line(f'{name_t} {name}_s;')
        if expr.direction == 'in':
            writer.line(f'assign {name}_s = {name}.data;')
        else:
            writer.line(f'assign {name}.data = {name}_s;')

        writer.line()

    for name, expr in ctx.variables.items():
        name_t = typedef_or_inline(writer, expr.dtype, name)
        writer.line(f'{name_t} {name};')
        writer.line()

    for c, s in zip(ctx.submodules, subsvmods):
        port_map = {}
        for intf, p in zip(c.in_ports, c.gear.in_ports):
            port_map[p.basename] = intf.name

        for intf, p in zip(c.out_ports, c.gear.out_ports):
            port_map[p.basename] = intf.name

        writer.block(s.get_inst(template_env, port_map))

    for f_hdl, f_ctx in funcs:
        size = ''
        if int(f_hdl.ret_dtype) > 0:
            size = f'[{int(f_hdl.ret_dtype)-1}:0]'

        if getattr(f_hdl.ret_dtype, 'signed', False):
            size = f'signed {size}'

        writer.line(f'function {size} {f_hdl.name};')

        writer.indent += 4

        for name, expr in f_ctx.args.items():
            name_t = typedef_or_inline(writer, expr.dtype, name)
            writer.line(f'input {name_t} {name};')
            writer.line()

        writer.indent -= 4

        svcompile(f_hdl,
                  writer,
                  f_ctx,
                  '',
                  selected=lambda x: True,
                  aux_funcs=aux_funcs)

    if ctx.regs:
        writer.line(f'initial begin')
        for name, expr in ctx.regs.items():
            writer.line(f"    {svexpr(ctx.ref(name))} = {svexpr(expr.val)};")

        writer.line(f'end')

    for name, expr in ctx.regs.items():
        writer.block(
            REG_TEMPLATE.format(svexpr(ctx.ref(name)), svexpr(expr.val)))

    for name, expr in ctx.regs.items():
        svcompile(hdl,
                  writer,
                  ctx,
                  name,
                  selected=lambda x: x.obj == expr,
                  aux_funcs=aux_funcs)

    for name, expr in ctx.variables.items():
        svcompile(hdl,
                  writer,
                  ctx,
                  name,
                  selected=lambda x: x.obj == expr,
                  aux_funcs=aux_funcs)

    for name, expr in ctx.intfs.items():
        svcompile(hdl,
                  writer,
                  ctx,
                  name,
                  selected=lambda x: x.name == name,
                  aux_funcs=aux_funcs)

    writer.lines[0:0] = aux_funcs.values()


def compile_gear_body(gear, outdir, template_env):
    # ctx, hdl_ast = parse_gear_body(gear)
    from pygears.hls2.translate import translate_gear
    ctx, hdl_ast = translate_gear(gear)

    subsvmods = []
    if ctx.submodules:
        from pygears.hdl import hdlgen
        svgen_map = registry("svgen/map")
        for c in ctx.submodules:
            rtl_top = hdlgen(c.gear, outdir=outdir, generate=False)
            svmod = svgen_map[rtl_top]
            subsvmods.append(svmod)

    funcs = []

    def _get_funcs_rec(block):
        for f_ast, f_ctx in block.funcs:
            funcs.append((f_ast, f_ctx))
            _get_funcs_rec(f_ast)

    _get_funcs_rec(hdl_ast)

    gear.child.clear()

    writer = HDLWriter()
    write_module(ctx,
                 hdl_ast,
                 writer,
                 subsvmods,
                 funcs,
                 template_env,
                 config=gear.params.get('hdl', {}))

    return '\n'.join(writer.lines), subsvmods


def compile_gear(gear, template_env, module_name, outdir):
    context = {
        'module_name': module_name,
        'intfs': template_env.port_intfs(gear),
        'sigs': gear.params['signals'],
        'params': gear.params
    }

    context['svlines'], subsvmods = compile_gear_body(gear, outdir,
                                                      template_env)

    return template_env.render_string(gear_module_template, context), subsvmods
