`ifndef SOCKET_CONSUMER_DRIVER_SV
 `define SOCKET_CONSUMER_DRIVER_SV

class socket_consumer_driver#(type DATA_T = bit [15:0]);

   virtual dti_verif_if#(DATA_T) vif;
   string  name;

	 chandle handle;

   function new
     (
      virtual dti_verif_if#(DATA_T) vif,
      string  name = "socket_consumer_driver"
      );
      this.vif = vif;
      this.name = name;
	    handle = sock_open("tcp://localhost:1234", name);
   endfunction

   task init();
      vif.cb_consumer.ready <= 1'b0;
      @(negedge vif.rst);
   endtask

   task main();
      init();
      get_and_drive();
	    sock_close(handle);
   endtask

   task get_and_drive();
      int ret;
      bit[$bits(DATA_T)-1 : 0] data;

      forever begin
         vif.cb_consumer.ready <= 1'b1;

         // @(vif.cb_consumer iff vif.cb_consumer.valid);
         @(negedge vif.clk iff vif.valid);
         // data = vif.cb_consumer.data;
         data = vif.data;
         ret = sock_put(handle, data);
         `verif_info($sformatf("Consumer driver %s sent: %p at %0t", name, DATA_T'(data), $time), 2);
         if (ret == 1) break;
      end

   endtask

endclass

`endif
