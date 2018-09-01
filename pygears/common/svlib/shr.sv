module shr #(
             parameter SIGNED = 0
             )
	 (
	  input logic clk,
	  input logic rst,
	  dti.consumer din,
    dti.consumer cfg,
	  dti.producer dout
	  );

   logic        handshake;
   assign handshake = dout.valid & dout.ready;
   assign cfg.ready = handshake;

   assign dout.valid = din.valid & cfg.valid;
   assign din.ready = handshake;

   if (SIGNED) begin
      assign dout.data = signed'(din.data) >> (cfg.data);
   end else begin
      assign dout.data = din.data >> (cfg.data);
   end

endmodule
