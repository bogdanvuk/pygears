module spy
   (
    input rst,
    input clk,
	  dti.consumer din,
	  dti.producer dout
    );
   assign dout.valid = 1;
   assign din.ready = 1;
   assign dout.data = din.data;
endmodule
