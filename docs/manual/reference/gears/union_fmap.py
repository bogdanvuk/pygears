from bdp import block, cap, path, text, fig, prev, p, poffx

part = block(text_margin=p(0.5, 0.5),
             alignment="nw",
             dotted=True,
             group='tight',
             group_margin=[p(1, 3), p(1, 2)])

comp = block(size=p(4, 4), nodesep=(5, 2))
ps_comp = block(size=p(6, 6), nodesep=(2, 3))
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(style=(None, bus_cap),
           line_width=0.3,
           double=True,
           border_width=0.06)
bus_text = text(font="\\scriptsize", margin=p(0, 0.5))

functor = part("Union fmap")
functor['mux'] = comp("mux", size=(4, 4))
functor['f1'] = comp(r"$-1$",
                     size=(4, 3)).right(functor['mux']).aligny(
                         functor['mux'].w(1),
                         prev().s(0))

functor['concat'] = comp("demux", size=(4, 4)).right(functor['f1']).aligny(
    functor['mux'].p)

prod2mux = bus(functor['mux'].w(0.5) - p(4, 0), functor['mux'].w(0.5))
fig << prod2mux
fig << bus_text("(i16, u16)").align(prod2mux.pos(0.5), prev().s(0.5, 0.2))

conn = bus(functor['mux'].e(1),
           functor[f'f1'].w(0.5) - (2, 0),
           functor[f'f1'].w(0.5),
           routedef='-|')
fig << bus_text("i16").align(conn.pos(0), prev().s(-0.4, 0.1))
fig << conn

conn = bus(functor[f'f1'].e(0.5),
           functor[f'f1'].e(0.5) + (2, 0),
           functor['concat'].w(1),
           routedef='|-')
fig << bus_text("i17").align(conn.pos(1), prev().s(1.4, 0.1))
fig << conn

conn = bus(functor['mux'].e(3),
           functor['concat'].w(3))
fig << bus_text("u16").align(conn.pos(0), prev().s(-0.4, 0.1))
fig << conn

con2cons = bus(functor['concat'].e(0.5), poffx(4))
fig << con2cons
fig << bus_text("(i17, u16)").align(con2cons.pos(0.5), prev().s(0.5, 0.2))

fig << functor

# render_fig(fig)
