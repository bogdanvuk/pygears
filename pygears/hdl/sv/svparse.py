import re

port_list_regex = r'\((?P<port_list>[\s\S]*?)\)'
generic_list_regex = r'(?:#\s*\((?P<param_list>[\s\S]*?)\))'
range_regex = r"(?:\[(?P<arr_high>[\s\S]*?):(?P<arr_low>[\s\S]*?)\])?"
space_regex = r'\s+'
opt_space_regex = r'\s*'
id_regex_t = r'(?P<{}>[\w"]+)'

module_regex = r'module' + space_regex + id_regex_t.format("name") + \
               opt_space_regex + generic_list_regex + "?" + opt_space_regex + \
               port_list_regex

simple_port_regex = "(?P<dir>input|output)" + opt_space_regex + \
                    id_regex_t.format("type") + \
                    "?" + space_regex + range_regex + opt_space_regex + id_regex_t.format("name")

param_regex = r'(?:parameter\s+)?' + id_regex_t.format("name") + \
              opt_space_regex + "=" + opt_space_regex + id_regex_t.format("val")

intf_port_regex = id_regex_t.format("type") + "\." + id_regex_t.format("modport") + \
                  space_regex + id_regex_t.format("name") + opt_space_regex + \
                  "(?:\[(?P<arr_high>[\s\S]*?):(?P<arr_low>[\s\S]*?)\])?"


def extract_ports(port_list):
    port_defs = [p.strip() for p in port_list.split('\n')]

    intfs = []
    ports = []
    for p in port_defs:
        # p = re.sub(r'//.*\n', '\n', p).strip()
        try:
            ret = re.search(simple_port_regex, p)
            if ret:
                ports.append(ret.groupdict())
                if ports[-1]["type"] is None:
                    ports[-1]["type"] = ""
            else:
                ret = re.search(intf_port_regex, p)
                intfs.append(ret.groupdict())
        except:
            pass

    return ports, intfs


def extract_params(param_list):
    if param_list is None:
        return []
    if not param_list.strip():
        return []
    else:
        param_defs = [p.strip() for p in param_list.split(',')]
        params = {}
        for p in param_defs:
            ret = re.search(param_regex, p)
            res = ret.groupdict()
            params[res['name']] = res

        return params


def parse(content):

    content = re.sub(r'//.*\n', '\n', content)
    ret = re.search(module_regex, content)

    ports, intfs = extract_ports(ret["port_list"])
    params = extract_params(ret["param_list"])

    return ret["name"], ports, intfs, params


# with open('/data/projects/pygears/pygears/lib/svlib/rng.sv', 'r') as f:
#     print(parse(f.read()))
