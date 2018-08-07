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
      string  name = "socket_producer_driver",
      int     port = 1234
      );
      this.vif = vif;
      this.name = name;
	    handle = sock_open($sformatf("tcp://localhost:%d", port), name);
   endfunction

   task init();
      vif.valid <= 1'b0;
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

      forever begin

         do begin
            @(posedge vif.clk);
            vif.valid <= 1'b0;
	          ret = sock_get(handle, data);
            `verif_info($sformatf("%s sock_get: %d ast %0t", name, ret, $time), 1);
            if (ret == 1) return;
         end while (ret == 2);

         `verif_info($sformatf("%s start driving item: %p at %0t", name, DATA_T'(data), $time), 2);

         vif.valid <= 1'b1;
         vif.data <= data;

         do begin
            @(negedge vif.clk);
            #1;
         end while(!vif.ready);

         `verif_info($sformatf("%s finished driving item: %p at %0t", name, DATA_T'(data), $time), 2);
         ret = sock_done(handle);
         if (ret == 1) return;
      end
   endtask : get_and_drive

endclass

`endif
