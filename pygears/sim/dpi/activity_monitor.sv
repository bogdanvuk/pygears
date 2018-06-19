`ifndef ACTIVITY_MONITOR_SV
 `define ACTIVITY_MONITOR_SV

class activity_monitor#(type DATA_T = bit [15:0], parameter int ACTIVITY_TIMEOUT = 1000);

   virtual dti_verif_if#(DATA_T) vif;
   string  name;

   function new
     (
      virtual dti_verif_if#(DATA_T) vif,
      string  name = "activity_monitor"
      );
      this.vif = vif;
      this.name = name;
   endfunction

   task main();
      int cnt;
      cnt = 0;
      forever begin
         @(vif.cb_monitor);
         if (vif.cb_monitor.valid && vif.cb_monitor.ready) begin
            cnt = 0;
         end else begin
            cnt++;
         end

         if (cnt == ACTIVITY_TIMEOUT) begin
            $display("Activiti monitor %s timedout", name);
            break;
         end
      end
   endtask

endclass

`endif
