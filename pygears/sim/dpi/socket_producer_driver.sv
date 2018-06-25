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
      @(vif.cb_producer iff !vif.rst);
   endtask

   task main();
      init();
      get_and_drive();
	    sock_close(handle);
   endtask

   task get_and_drive();
      bit[$bits(DATA_T)-1 : 0] data;
      int ret;

      forever begin
	       ret = sock_get(handle, data);
         if (ret == 1) break;
         if (ret == 2) begin
            $display("Driver %s got ret 2 at %0t", name, DATA_T'(data), $time);
            @(vif.cb_producer);
            continue;
         end

         $display("Start driving item: %p at %0t", DATA_T'(data), $time);

         vif.cb_producer.valid <= 1'b1;
         vif.cb_producer.data <= data;

         // wait for handshake
         // @(vif.cb_producer iff vif.cb_producer.ready);
         @(negedge vif.clk iff vif.ready);

         vif.cb_producer.valid <= 1'b0;

         $display("Finished driving item: %p", DATA_T'(data));
         ret = sock_done(handle);
         if (ret == 1) break;
      end
   endtask : get_and_drive

endclass

`endif
