`ifndef DTI_VERIF_IF_SV
`define DTI_VERIF_IF_SV

interface dti_verif_if #(
                         type DATA_T = bit [15:0]
                         )
   (
    input logic clk,
    input logic rst
    );

   logic [$bits(DATA_T)-1:0] data;
   logic valid;
   logic ready;

   bit   checks_enable = 1;
   bit   coverage_enable = 1;
   string name;

   // ---------------------------------------------------------------------------
   // Checks
   // ---------------------------------------------------------------------------

   // data isn't X or HiZ when valid is asserted
   asrt_unknown_data : assert property (
      @(posedge clk) disable iff(!checks_enable || rst)
      valid |-> !$isunknown(data))
   else
      $display("%s: Data either X or HiZ", name);

   // valid is never X or HiZ
   asrt_unknown_valid : assert property (
      @(posedge clk) disable iff(!checks_enable || rst)
      !$isunknown(valid))
   else
      $display("%s: Valid either X or HiZ", name);

   // ready is never X or HiZ
   asrt_unknown_ready : assert property (
      @(posedge clk) disable iff(!checks_enable || rst)
      !$isunknown(ready))
   else
      $display("%s: Ready either X or HiZ", name);

   // when valid is asserted when ready is low, it must hold until
   // ready is asserted and transaction is completed
   asrt_hold_valid : assert property (
      @(posedge clk) disable iff(!checks_enable || rst)
      valid & ~ready |=> valid && $stable(data))
   else
      $display("%s: Valid or data changed before handshake completed", name);

   // sync. reset active high
   // asrt_rst : assert property (
   //    @(posedge clk) disable iff(!checks_enable)
   //    rst |-> ##[0:1] ~valid & ~eot & ~ready)
   // else
   //   $display("Valid, eot or ready not low during reset", name);

   // ---------------------------------------------------------------------------
   // Coverage
   // ---------------------------------------------------------------------------

   // valid asserted when ready high
   cp_valid_with_ready : cover property (
      @(posedge clk) disable iff(!coverage_enable || rst)
      valid |-> ready);

   // valid asserted when ready low
   cp_valid_without_ready : cover property (
      @(posedge clk) disable iff(!coverage_enable || rst)
      valid |-> !ready);

endinterface

`endif
