import jinja2


@jinja2.contextfilter
def call_macro_by_name(context, macro_name, *args, **kwargs):
    return context.vars[macro_name](*args, **kwargs)


jenv = jinja2.Environment()
jenv.filters['macro'] = call_macro_by_name

qrange_mux_str = '''
{% macro qrange_mux_macro(iter_name, iter_reg, flag_name, rng) %}

if {{flag_name}}:
    {{iter_name}} = {{iter_reg}}
else:
    {{iter_name}} = {{rng[0]}}

{{iter_reg}} = {{iter_name}} + {{rng[2]}}

{{flag_name}} = True

{% endmacro %}
'''

qrange_mux_impl = jenv.from_string(qrange_mux_str).module.qrange_mux_macro

enumerate_str = '''
{% macro enumerate_macro(idx_name, iter_name, var_name, rng) %}

{% for i in rng %}
if {{idx_name}} == {{i}}:
    {{iter_name}} = {{var_name}}{{i}}
{% endfor %}

{% endmacro %}
'''

enumerate_impl = jenv.from_string(enumerate_str).module.enumerate_macro
