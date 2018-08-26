from bdp import block, p, group, cap, path, text, fig, prev, render_fig

bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(
    color="black!40",
    style=('', bus_cap),
    shorten=p(0.2, 0.2),
    line_width=0.3,
    border_width=0.06,
    double=True)
bus_text = text(font="\\footnotesize", margin=p(0.4, 0.2))

gear = block(size=p(4, 2), nodesep=p(2, 2))

echo_sim = block(
    "mono_echo_sim",
    text_margin=p(0.5, 0.5),
    alignment="nw",
    dotted=True,
    group='tight',
    group_margin=[p(2, 3), p(2, 1)],
    text_font="\\Large")

echo_sim['drv'] = gear('drv')
echo_sim['echo'] = gear('echo').right(echo_sim['drv'])
echo_sim['collect'] = gear('collect').right(echo_sim['echo'])

fig << bus(echo_sim['drv'].e(0.5), echo_sim['echo'].w(0.5))
fig << bus(echo_sim['echo'].e(0.5), echo_sim['collect'].w(0.5))

fig << echo_sim

# render_fig(fig)
