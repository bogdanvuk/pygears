from bdp import block, p, group, cap, path, text, poffx, poffy, prectx, fig, render_fig, cur, prev

mul_block = block("x", size=p(2, 2), shape='circle')
add_block = block("+", size=p(2, 2), shape='circle')
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(
    color="black!40",
    style=('', bus_cap),
    shorten=p(0.2, 0.2),
    line_width=0.3,
    border_width=0.06,
    double=True)
bus_text = text(font="\\footnotesize", margin=p(0.4, 0.2))

echo = block(
    "Echo",
    text_margin=p(0.5, 0.5),
    alignment="nw",
    dotted=True,
    group='tight',
    group_margin=[p(2, 3), p(2, 1)],
    text_font="\\Large")


def make_external(pos, direction='o', pin_extrude=2, **kwds):
    if direction == 'o':
        style = ('', bus_cap)
    else:
        style = (bus_cap, '')
    return bus(
        pos, poffx(echo.w() - pos - p(pin_extrude, 0)), style=style, **kwds)


echo['add'] = add_block()
echo['fifo'] = block("FIFO", size=p(5, 3)).align(echo['add'].p + p(18, 3))

echo['dout'] = bus(
    echo['add'].e(0.5),
    prectx(echo['fifo'].n(1.0) + p(1, 1)),
    echo['fifo'].e(0.5),
    shorten=p(0.2, 0.2),
    routedef='|-')

echo['fill'] = block(
    "Fill Void", size=p(3, 5)).align(echo['fifo'].w(0.5) - p(2, 0),
                                     cur().e(1))
echo += bus(echo['fill'].e(4), poffx(6), style=(bus_cap, None))
echo += text("0").align(echo[-1][-1] + p(0.5, 0), cur().c())
echo += bus(echo['fifo'].w(0.5), echo['fill'].e(1))
echo['mul'] = mul_block().align(echo['fill'].w(0.5) - p(2, 0), cur().e(0.5))
echo += bus(echo['fill'].w(0.5), echo['mul'].e(0.5))

echo['shr'] = block(
    "SHR", size=p(3, 3)).align(echo['mul'].w(0.5) - p(2, 0),
                               cur().e(0.5))
echo += bus(echo['mul'].w(0.5), echo['shr'].e(0.5))

echo += bus(echo['shr'].w(0.5), echo['add'].s(0.5), routedef='-|')

echo += bus(
    echo['mul'].s(0.5),
    poffy(4),
    poffx(-8.5),
    routedef='-|',
    style=(bus_cap, None))
echo += bus_text("Feedback gain").align(echo[-1].pos(1), prev().e(0.5))

echo += bus(
    echo['shr'].s(0.5),
    poffy(2),
    poffx(-4),
    routedef='-|',
    style=(bus_cap, None))
echo += bus_text("Precision").align(echo[-1].pos(1), prev().e(0.5))

fig << make_external(echo['add'].w(0.5), direction='i')
fig << bus_text("din").aligny(echo['add'].w(0.5),
                              prev().s()).alignx(echo.w(),
                                                 prev().s(1.0))

fig << echo

fig << bus(echo['add'].e(0.5), echo['fifo'].n(1.0) + p(5, -2))

fig << bus_text("dout").aligny(fig[-1][1],
                               prev().s()).alignx(fig[-1][1],
                                                  prev().s(0.5))

render_fig(fig)
