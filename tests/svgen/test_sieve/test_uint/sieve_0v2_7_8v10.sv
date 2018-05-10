
module sieve_0v2_7_8v10
(
    input clk,
    input rst,
    dti.consumer din, // u10 (10)
    dti.producer dout // u5 (5)

);

   assign dout.data = {din.data[9:8], din.data[7:7], din.data[1:0]};

   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule