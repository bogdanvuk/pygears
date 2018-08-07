module shr
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
   assign dout.data = signed'(din.data) >> (cfg.data);
   assign din.ready = handshake;

endmodule
