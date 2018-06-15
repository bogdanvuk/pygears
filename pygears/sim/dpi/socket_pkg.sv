`ifndef SOCKET_PKG_SV
 `define SOCKET_PKG_SV

package socket_pkg;

   typedef class socket_producer_driver;
   typedef class socket_consumer_driver;

 `include "socket_producer_driver.sv"
 `include "socket_consumer_driver.sv"

endpackage : socket_pkg

 `include "dti_verif_if.sv"

`endif
