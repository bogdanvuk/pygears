from pygears import config

config['debug/trace'].append('/fmap/sub.*')
config['debug/trace'].append('/fmap.din')
config['debug/trace'].append('/fmap.dout')
