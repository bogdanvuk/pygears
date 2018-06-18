`ifndef SOCKET_PRODUCER_DRIVER_SV
 `define SOCKET_PRODUCER_DRIVER_SV

import sock::*;

class socket_producer_driver #(type DATA_T = bit [15:0]);

   virtual dti_verif_if#(DATA_T) vif;
   string  name;

	 chandle handle;

   function new
     (
      virtual dti_verif_if#(DATA_T) vif,
      string  name = "socket_producer_driver"
      );
      this.vif = vif;
      this.name = name;
	    handle = sock_open("tcp://localhost:1234", name);
   endfunction

   task init();
      vif.cb_producer.valid <= 1'b0;
      @(negedge vif.rst);
   endtask

   task main();
      init();
      get_and_drive();
	    sock_close(handle);
   endtask

   task get_and_drive();
      bit[$bits(DATA_T)-1 : 0] data;
      int ret;

	    while(sock_get(handle, data) == 0) begin
         $display("Start driving item: %p", DATA_T'(data));

         vif.cb_producer.valid <= 1'b1;
         vif.cb_producer.data <= data;

         // wait for handshake
         @(vif.cb_producer iff vif.cb_producer.ready);

         vif.cb_producer.valid <= 1'b0;

         $display("Finished driving item: %p", DATA_T'(data));
         ret = sock_done(handle);
         if (ret == 1) break;
      end
   endtask : get_and_drive

endclass

`endif
