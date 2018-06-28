`ifndef SOCKET_MACROS_SV
 `define SOCKET_MACROS_SV

 `define verif_info(msg, ver) \
begin\
 `ifdef VERBOSITY\
   if (ver > `VERBOSITY)\
     $display(msg);\
 `else\
   $display(msg);\
 `endif\
end\

`endif
