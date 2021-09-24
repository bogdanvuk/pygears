from pygears import reg
from pygears.hls import ir, is_intf_id
from pygears.hls import Context, HDLVisitor, Scope
from pygears.typing import Bool, typeof
from pygears.core.port import HDLProducer, HDLConsumer
from pygears.core.gear import InSig, OutSig
from dataclasses import dataclass, field
from typing import List
import itertools
from pygears.hdl.sv.v.accessors import rewrite

from .util import svgen_typedef
from .v.util import vgen_signal, vgen_intf

# REG_TEMPLATE = """
# always @(posedge clk) begin
#     if(rst | _rst_cond) begin
#         {0} <= {1};
#     end else if ({0}_en && cycle_done) begin
#         {0} <= {0}_next;
#     end
# end
# """
REG_TEMPLATE = """
always @(posedge clk) begin
    if (rst || (({2}) && _state_en)) begin
        {0} <= {1};
    end else if (_state_en) begin
        {0} <= {0}_next;
    end
end
"""

REG_TEMPLATE_NO_RST_COND = """
always @(posedge clk) begin
    if (rst) begin
        {0} <= {1};
    end else if (_state_en) begin
        {0} <= {0}_next;
    end
end
"""


class HDLWriter:
    def __init__(self, indent=0):
        self.indent = indent
        self.lines = []

    def line(self, line=''):
        if not line:
            self.lines.append('')
        else:
            self.lines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)

    def __str__(self):
        return '\n'.join(self.lines)


res_true = ir.ResExpr(Bool(True))


@dataclass
class BlockLines:
    header: List = field(default_factory=list)
    content: List = field(default_factory=list)
    footer: List = field(default_factory=list)


def is_reg_id(expr):
    return (isinstance(expr, ir.Name) and isinstance(expr.obj, ir.Variable) and expr.obj.reg)


class SVCompiler(HDLVisitor):
    def __init__(self, ctx, var, writer, selected, lang, aux_funcs=None):
        self.ctx = ctx
        self.writer = writer
        self.var = var
        self.selected = selected
        self.block_lines = []
        self.block_stack = []
        self.defaults = Scope()
        self.lang = lang

        if self.lang == 'sv':
            from .sv_expression import svexpr
            self.separator = '.'
            self.svexpr = svexpr
        else:
            from .v.v_expression import vexpr
            self.separator = '.'
            self.svexpr = vexpr

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

        if not isinstance(block, ir.HDLBlock):
            return

    def exit_block(self, block=None):
        self.defaults.upscope()

        bl = self.block_lines.pop()

        if isinstance(block, ir.Branch):
            maybe_else = 'else ' if getattr(block, 'else_branch', False) else ''
            # in_cond = ir.BinOpExpr((block.in_cond, block.opt_in_cond),
            #                        ir.opc.And)

            in_cond = block.test

            if in_cond != res_true:
                in_cond_val = self.svexpr(in_cond, self.aux_funcs)

                bl.header.append(f'{maybe_else}if ({in_cond_val}) begin')
            elif maybe_else:
                bl.header.append(f'else begin')

        self.write(bl)

        self.block_stack.pop()

    def handle_defaults(self, target, stmt):
        if target not in self.defaults:
            self.defaults.items[target] = stmt
        elif stmt != self.defaults[target]:
            self.defaults[target] = stmt
            self.write(stmt)

    def attr(self, *args):
        return self.separator.join(args)

    def _assign_value(self, target, val):
        if isinstance(target, ir.SubscriptExpr):
            base_target = target.val
        elif isinstance(target, ir.Name):
            base_target = target
        elif isinstance(target, ir.Component):
            base_target = target.val
        elif isinstance(target, ir.ConcatExpr):
            for i, t in enumerate(target.operands):
                self._assign_value(t, ir.SubscriptExpr(val, ir.ResExpr(i)))

            return
        else:
            raise Exception

        if is_reg_id(base_target):

            if not self.selected(base_target):
                return

            name = self.svexpr(target, self.aux_funcs)

            val = self.svexpr(val, self.aux_funcs)
            if val is None:
                return

            svstmt = f"{name} = {val}"

            # if this is only partial assignement, the order of assignment then
            # matters and this cannot be a default
            if isinstance(target, ir.SubscriptExpr):
                self.write(svstmt)
            else:
                self.handle_defaults(name, svstmt)

            if name == '_state_next':
                self.handle_defaults("_state_en", "_state_en = 1")

            return

        if target.dtype is OutSig:
            if self.selected(target):
                name = target.obj.val.name
                svval = self.svexpr(val, self.aux_funcs)
                svstmt = f"{name} = {svval}"
                self.handle_defaults(name, svstmt)
            return
        elif isinstance(target, ir.Component):
            name = self.svexpr(base_target, self.aux_funcs)
            if target.field == 'data':
                if self.selected(base_target):
                    self.handle_defaults(self.attr(name, 'valid'),
                                         f"{self.attr(name, 'valid')} = 1")
                    val = self.svexpr(val, self.aux_funcs)
                    if val is not None:
                        svstmt = f"{name}_s = {val}"
                        self.handle_defaults(name, svstmt)
            elif target.field == 'ready' and self.selected(base_target):
                self.handle_defaults(self.attr(name, 'ready'), f"{self.attr(name, 'ready')} = 1")

            return
        elif is_intf_id(target):
            if is_intf_id(val) and self.selected(val):
                name = self.svexpr(base_target, self.aux_funcs)
                val_name = self.svexpr(val, self.aux_funcs)
                svstmt = f"{name}_s = {val_name}_s"
                self.handle_defaults(name, svstmt)
                self.write(f"{self.attr(name, 'valid')} = {self.attr(val_name, 'valid')}")
                self.write(f"{self.attr(val_name, 'ready')} = {self.attr(name, 'ready')}")

            return

        if not self.selected(base_target):
            return

        if val.dtype is None:
            return

        target = self.svexpr(target, self.aux_funcs)

        if target is None:
            return

        val = self.svexpr(val, self.aux_funcs)
        if val is None:
            return

        svstmt = f"{target} = {val}"

        self.handle_defaults(target, svstmt)

    def AssertValue(self, node):
        self.write(f'assert ({self.svexpr(node.val.test, self.aux_funcs)})')
        self.write(f'else $error("{node.val.msg}");')

    def AssignValue(self, node):
        self._assign_value(node.target, node.val)

    def list_initials(self):
        for name, obj in self.ctx.scope.items():
            if not isinstance(obj, ir.Variable):
                continue

            if typeof(obj.dtype, ir.IntfType):
                # if isinstance(obj.val.producer, HDLProducer):
                if (self.selected(self.ctx.ref(name, ctx='store'))
                        and obj.dtype.direction == ir.IntfType.iout):
                    yield self.attr(name, 'valid'), '0'
                # elif len(obj.val.consumers) == 1 and isinstance(obj.val.consumers[0], HDLConsumer):
                elif self.selected(self.ctx.ref(name, ctx='ready')):
                    if not is_port_intf(name, self.ctx):
                        yield self.attr(name, 'ready'), f"{self.attr(name, 'valid')} ? 0 : 1'bx"

            elif obj.reg:
                target = self.ctx.ref(name)
                if self.selected(target):
                    if name == '_state':
                        yield '_state_en', '0'

                    yield (f'{self.svexpr(self.ctx.ref(name, ctx="store"), self.aux_funcs)}',
                           f'{self.svexpr(self.ctx.ref(name), self.aux_funcs)}')
            else:
                pass

    def Module(self, node):
        self.block_lines.append(BlockLines())

        self.header(f'// Comb block for: {self.var}')
        self.header(f'always_comb begin')

        for target, expr in self.list_initials():
            self.handle_defaults(target, f"{target} = {expr}")
            # self.prepend(f"{target} = {stmt}")
            # self.defaults[target] = stmt

        self.BaseBlock(node)

        self.trim_cur_block()

        for target, svstmt in reversed(list(self.defaults.items.items())):
            self.prepend(svstmt)

        self.footer('end')

    def FuncReturn(self, node):
        retval = self.svexpr(node.expr, self.aux_funcs)

        if self.lang == 'sv':
            if retval is None:
                self.write('return')
            else:
                self.write(f"return {self.svexpr(node.expr, self.aux_funcs)}")
        else:
            if retval is not None:
                self.write(
                    f"{self.svexpr(node.func.name, self.aux_funcs)} = {self.svexpr(node.expr, self.aux_funcs)}"
                )

    def FuncBlock(self, node):
        self.block_lines.append(BlockLines())

        self.header('')

        self.BaseBlock(node)

        self.footer(f'endfunction')
        self.footer('')

    def LoopBlock(self, node):
        raise Exception()

    def BaseBlock(self, node):
        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

        self.trim_cur_block()

        self.exit_block(node)

    def HDLBlock(self, node):
        self.enter_block(node)

        for i, b in enumerate(node.branches):
            if i > 0:
                b.else_branch = True
            else:
                b.else_branch = False

            self.visit(b)

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


def svcompile(hdl_stmts, ctx, title, selected, lang, aux_funcs=None):
    writer = HDLWriter()
    v = SVCompiler(ctx, title, writer, selected=selected, lang=lang, aux_funcs=aux_funcs)
    v.visit(hdl_stmts)

    if not v.block_lines[0].content:
        return ''

    write_block(v.block_lines[0], writer)
    writer.line()
    return str(writer)


# TODO: Why do we need this check, can we generalize this for any variable?
def is_top_port_intf(name, ctx):
    for p in ctx.gear.in_ports + ctx.gear.out_ports:
        if p.basename == name:
            return p
    else:
        return None


def is_port_intf(name, ctx):
    for m in ctx.submodules:
        for p in m.in_ports:
            if p.name == name:
                return p

    for p in ctx.gear.in_ports:
        if p.basename == name:
            if p.consumer:
                return p
            else:
                return None

    for p in ctx.gear.out_ports:
        if p.basename == name:
            return p


def write_declarations(ctx, subsvmods, template_env):
    writer = HDLWriter()

    lang = template_env.lang

    if lang == 'sv':
        from .sv_expression import svexpr
        sep = '.'
        exprgen = svexpr
    else:
        from .v.v_expression import vexpr
        sep = '.'
        exprgen = vexpr

    # TODO: Fix not to require this check
    if '_state_en' not in ctx.scope:
        writer.line(f'logic _state_en;')

    for name, expr in ctx.regs.items():
        name = exprgen(ctx.ref(name))

        if lang == 'sv':
            name_t = typedef_or_inline(writer, expr.dtype, name)
            writer.line(f'{name_t} {name}, {name}_next;')
        else:
            writer.block(vgen_signal(expr.dtype, 'reg', f'{name}_next', 'output', hier=False))
            writer.block(vgen_signal(expr.dtype, 'reg', name, 'output', hier=False))

        writer.line()

    for name, expr in ctx.intfs.items():
        dtype = expr.dtype.dtype
        if is_top_port_intf(name, ctx) is None:
            if lang == 'sv':
                writer.line(f'dti#({dtype.width}) {name}();')
            else:
                writer.line(f'reg {name}_ready;')
                writer.line(f'reg {name}_valid;')
                writer.line(vgen_signal(dtype, 'reg', f'{name}_data', 'output', False))

        if lang == 'sv':
            name_t = typedef_or_inline(writer, dtype, name)
            writer.line(f'{name_t} {name}_s;')

            if expr.dtype.direction == ir.IntfType.iin:
                writer.line(f'assign {name}_s = {sep.join([name, "data"])};')
            else:
                writer.line(f'assign {sep.join([name, "data"])} = {name}_s;')

        else:
            if expr.dtype.direction == ir.IntfType.iin:
                writer.block(vgen_signal(dtype, 'reg', f'{name}_s', 'input', False))
                writer.line(f"assign {name}_s = {name}_data;")
            else:
                writer.block(vgen_signal(dtype, 'reg', f'{name}_s', 'output', False))
                writer.line(f"assign {name}_data = {name}_s;")

        writer.line()

    for name, expr in ctx.variables.items():
        if expr.dtype is None or typeof(expr.dtype, ir.IntfType) or expr.reg:
            continue

        if lang == 'sv':
            name_t = typedef_or_inline(writer, expr.dtype, name)
            writer.line(f'{name_t} {name};')
        else:
            writer.block(vgen_signal(expr.dtype, 'reg', name, 'input', hier=False))

        writer.line()

    for c, s in zip(ctx.submodules, subsvmods):
        port_map = {}
        for intf, p in itertools.chain(zip(c.in_ports, c.gear.in_ports),
                                       zip(c.out_ports, c.gear.out_ports)):
            if lang == 'sv':
                port_map[p.basename] = intf.name
            else:
                port_map[p.basename] = (intf.name, None, None)

        writer.block(s.get_inst(template_env, port_map))

    if ctx.regs:
        writer.line(f'initial begin')
        for name, expr in ctx.regs.items():
            if not isinstance(expr.val, ir.ResExpr):
                continue

            writer.line(f"    {exprgen(ctx.ref(name))} = {exprgen(expr.val)};")

        writer.line(f'end')

    return str(writer)


def write_module(ctx: Context, hdl, writer, subsvmods, funcs, template_env, config=None):
    if config is None:
        config = {}

    lang = template_env.lang

    aux_funcs = {}

    if lang == 'sv':
        from .sv_expression import svexpr
        sep = '.'
        exprgen = svexpr
    else:
        from .v.v_expression import vexpr
        sep = '.'
        exprgen = vexpr

    for f_hdl, f_ctx in funcs:
        size = ''
        if f_hdl.ret_dtype.width > 0:
            size = f'[{f_hdl.ret_dtype.width-1}:0]'

        if getattr(f_hdl.ret_dtype, 'signed', False):
            size = f'signed {size}'

        writer.line(f'function {size} {f_hdl.name};')

        writer.indent += 4

        for name, expr in f_ctx.variables.items():
            if expr.dtype is None:
                continue

            if name in f_ctx.signature:
                continue

            if lang == 'sv':
                name_t = typedef_or_inline(writer, expr.dtype, name)
                writer.line(f'{name_t} {name};')
            else:
                writer.block(vgen_signal(expr.dtype, 'reg', name, 'input', hier=False))

            writer.line()

        if lang == 'sv':
            for name, dtype in f_ctx.signature.items():
                name_t = typedef_or_inline(writer, dtype, name)
                writer.line(f'input {name_t} {name};')
                writer.line()
        else:
            for name, dtype in f_ctx.signature.items():
                writer.block(vgen_signal(dtype, 'input', name, 'input', hier=False))
                writer.line()

            for name, dtype in f_ctx.signature.items():
                tmp = vgen_signal(dtype, 'reg', name, 'input', hier=False)
                writer.block('\n'.join(l for l in tmp.split('\n')[1:] if l.startswith('reg')))

            for name, dtype in f_ctx.signature.items():
                tmp = vgen_signal(dtype, 'reg', name, 'input', hier=False)
                for l in tmp.split('\n')[1:]:
                    if l.startswith('reg'):
                        continue

                    if l.startswith('assign'):
                        l = l[7:]

                    writer.line(l)

        writer.indent -= 4

        blk = svcompile(f_hdl, f_ctx, '', selected=lambda x: True, lang=lang, aux_funcs=aux_funcs)

        if lang == 'v':
            blk = vrewrite(f_ctx, blk)

        writer.line(blk)

    blk = write_declarations(ctx, subsvmods, template_env)

    for name, expr in ctx.regs.items():
        init = "'x" if expr.val is None else exprgen(expr.val)
        if not ctx.reset_states.get(name, None):
            blk += REG_TEMPLATE_NO_RST_COND.format(exprgen(ctx.ref(name)), init)
        else:
            rst_states = ctx.reset_states[name]
            # TODO: Find a better way to infer when the state register has been removed
            if '_rst_cond' not in ctx.scope:
                rst_expr = ' || '.join([f'(_state_next == {exprgen(s)})' for s in rst_states])
            else:
                rst_expr = ' || '.join([f'_rst_cond[{s}]' for s in rst_states])

            blk += REG_TEMPLATE.format(exprgen(ctx.ref(name)), init, rst_expr)

    for name, expr in ctx.regs.items():
        blk += svcompile(hdl,
                         ctx,
                         name,
                         selected=lambda x: x.obj == expr,
                         lang=lang,
                         aux_funcs=aux_funcs)

    for name, expr in ctx.variables.items():
        var_blk = svcompile(hdl,
                         ctx,
                         name,
                         selected=lambda x: x.obj == expr,
                         lang=lang,
                         aux_funcs=aux_funcs)

        if typeof(expr.dtype, ir.IntfType) and any(expr.name == p.basename for p in ctx.gear.in_ports):
            # TODO: Make this transformation somewhere else
            if len(ctx.gear.in_ports) == len(ctx.gear.out_ports) == 1:
                pin = ctx.gear.in_ports[0].basename
                pout = ctx.gear.out_ports[0].basename

                template = (
                    f'if ({pin}.valid) begin\n'
                    f'    if ({pout}.ready) begin\n'
                    f'        {pin}.ready = 1;\n'
                    f'    end\n'
                    f'end'
                )

                if all(t.strip() == v.strip() for t, v in zip(template.split('\n'), var_blk.split('\n')[3:8])):
                    var_blk = f'    assign {pin}.ready = {pout}.ready;'

        blk += var_blk

    for name, expr in ctx.signals.items():
        blk += svcompile(hdl,
                         ctx,
                         name,
                         selected=lambda x: x.obj == expr,
                         lang=lang,
                         aux_funcs=aux_funcs)

    # for name, expr in ctx.intfs.items():
    #     blk += svcompile(hdl,
    #                      ctx,
    #                      name,
    #                      selected=lambda x: x.name == name,
    #                      lang=lang,
    #                      aux_funcs=aux_funcs)

    if lang == 'v':
        blk = vrewrite(ctx, blk)

    writer.line(blk)

    writer.lines[0:0] = aux_funcs.values()


def vrewrite(ctx, body):
    index = {}
    for name, v in ctx.scope.items():
        if not isinstance(v, ir.Variable):
            continue

        index[name] = v.dtype
        if typeof(v.dtype, ir.IntfType):
            index[f'{name}_s'] = v.dtype.dtype
        else:
            if v.reg:
                index[f'{name}_next'] = v.dtype

    return rewrite(body, index)


def compile_gear_body(gear, outdir, template_env):
    # ctx, hdl_ast = parse_gear_body(gear)
    from pygears.hls.translate import translate_gear
    ctx, hdl_ast = translate_gear(gear)

    subsvmods = []
    if ctx.submodules:
        from pygears.hdl import hdlgen
        hdlgen_map = reg['hdlgen/map']
        for c in ctx.submodules:
            rtl_top = hdlgen(c.gear, outdir=outdir, generate=False)
            svmod = hdlgen_map[rtl_top]
            subsvmods.append(svmod)

    funcs = []

    def _get_funcs_rec(block):
        for f_ast, f_ctx in block.funcs:
            funcs.append((f_ast, f_ctx))
            _get_funcs_rec(f_ast)

    _get_funcs_rec(hdl_ast)

    writer = HDLWriter()
    write_module(ctx,
                 hdl_ast,
                 writer,
                 subsvmods,
                 funcs,
                 template_env,
                 config=gear.meta_kwds.get('hdl', {}))

    return '\n'.join(writer.lines), subsvmods


def compile_gear(gear, template_env, module_name, outdir, comment=None, attrib=None):
    # TODO: Harden the case where local variable shadows a global one
    context = {
        'module_name': module_name,
        'intfs': template_env.port_intfs(gear),
        'sigs': gear.meta_kwds['signals'],
        'params': gear.params,
        'comment': {
            'comment': comment,
            'attrib': [] if attrib is None else attrib
        }
    }

    context['svlines'], subsvmods = compile_gear_body(gear, outdir, template_env)

    return template_env.render_string(gear_module_template, context), subsvmods
