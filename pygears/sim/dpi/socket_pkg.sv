`ifndef SOCKET_PKG_SV
 `define SOCKET_PKG_SV

package socket_pkg;

   `include "socket_macros.svh"

   typedef class socket_producer_driver;
   typedef class socket_consumer_driver;
   typedef class activity_monitor;

 `include "socket_producer_driver.sv"
 `include "socket_consumer_driver.sv"
 `include "activity_monitor.sv"

endpackage : socket_pkg

 `include "dti_verif_if.sv"

`endif
