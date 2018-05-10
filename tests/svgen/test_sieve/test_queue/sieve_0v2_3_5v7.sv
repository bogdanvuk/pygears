
module sieve_0v2_3_5v7
(
    input clk,
    input rst,
    dti.consumer din, // [u2]^6 (8)
    dti.producer dout // [u2]^4 (6)

);

   assign dout.data = {din.data[7:6], din.data[4:4], din.data[2:0]};

   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule