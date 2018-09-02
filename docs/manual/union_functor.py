from bdp import block, cap, path, text, fig, prev, p

part = block(
    text_margin=p(0.5, 0.5),
    alignment="nw",
    dotted=True,
    group='tight',
    group_margin=[p(1, 3), p(1, 2)])

comp = block(size=p(6, 4), nodesep=(6, 2))
ps_comp = block(size=p(6, 6), nodesep=(2, 3))
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(
    style=(None, bus_cap), line_width=0.3, double=True, border_width=0.06)
bus_text = text(font="\\scriptsize", margin=p(0, 0.5))

functor = part("Union Functor")
functor['demux'] = comp("Demux", size=(4, 6))
functor['f1'] = comp(
    "u16 - 1", size=(4, 4)).right(functor['demux']).aligny(
        functor['demux'].w(2),
        prev().s(0))
functor['f2'] = comp("q8.8 - 1", size=(4, 4)).below(functor['f1'])

functor['mux'] = comp(
    "Mux", size=(4, 6)).right(functor['f1']).aligny(functor['demux'].p)

producer = comp("Producer").left(functor['demux']).aligny(
    functor['demux'].e(0.5),
    prev().e(0.5))
fig << producer
prod2demux = bus(producer.e(0.5), functor['demux'].w(0.5))
fig << prod2demux
fig << bus_text("u16 $|$ (u8, u8)").align(
    prod2demux.pos(0.5),
    prev().s(0.5, 0.2))

for i, t in enumerate(['u16', '(u8, u8)']):
    conn = bus(
        functor['demux'].e(i * 4 + 1),
        functor[f'f{i+1}'].w(0.5) - (2, 0),
        functor[f'f{i+1}'].w(0.5),
        routedef='-|')
    fig << bus_text(t).align(conn.pos(0), prev().s(-0.3, 0.1))
    fig << conn

    conn = bus(
        functor[f'f{i+1}'].e(0.5),
        functor[f'f{i+1}'].e(0.5) + (2, 0),
        functor['mux'].w(i * 4 + 1),
        routedef='|-')
    fig << bus_text(t).align(conn.pos(1), prev().s(1.3, 0.1))
    fig << conn

consumer = comp("Consumer").right(functor['mux']).aligny(
    functor['mux'].e(0.5),
    prev().e(0.5))
fig << consumer
con2cons = bus(functor['mux'].e(0.5), consumer.w(0.5))
fig << con2cons
fig << bus_text("u16 $|$ (u8, u8)").align(
    con2cons.pos(0.5),
    prev().s(0.5, 0.2))

ctrl = bus(functor['demux'].e(0.5), functor['mux'].w(0.5))
fig << ctrl
fig << bus_text("ctrl").align(ctrl.pos(0.5), prev().s(0.5))

fig << functor

# render_fig(fig)
