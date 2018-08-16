interface dti_spy #(
                    type data_type = logic
                    )(input spy_clk, spy_rst);

   data_type       data;
   logic           valid;
   logic           ready;
   logic           handshake;

   bit checks_enable = 0;

   assign handshake = valid && ready && !spy_clk;

   // data isn't X or HiZ when valid is asserted
   asrt_unknown_data : assert property (
      @(posedge spy_clk) disable iff(!checks_enable || spy_rst)
      valid |-> !$isunknown(data))
   else
      $error("%m: Data either X or HiZ");

   // valid is never X or HiZ
   asrt_unknown_valid : assert property (
      @(posedge spy_clk) disable iff(!checks_enable || spy_rst)
      !$isunknown(valid))
   else
      $error("%m: Valid either X or HiZ");

   // ready is never X or HiZ
   asrt_unknown_ready : assert property (
      @(posedge spy_clk) disable iff(!checks_enable || spy_rst)
      !$isunknown(ready))
   else
      $error("%m: Ready either X or HiZ");

   // when valid is asserted when ready is low, it must hold until
   // ready is asserted and transaction is completed
   asrt_hold_valid : assert property (
      @(posedge spy_clk) disable iff(!checks_enable || spy_rst)
      valid & ~ready |=> valid && $stable(data))
   else
      $error("%m: Valid or data changed before handshake completed");

   // each valid will be acknowledged
   asrt_handshake : assert property (
      @(posedge spy_clk) disable iff(!checks_enable)
      valid |-> s_eventually ready)
     else
       $warning("%m: Valid never got ready. Handshake didn't occur.");

   final begin
      integer f;
      if (valid) begin
         f = $fopen("activity.log", "a");
         $fwrite(f, "%m: spy interface was not acknowledged\n");
         $fclose(f);
      end
   end

endinterface : dti_spy
