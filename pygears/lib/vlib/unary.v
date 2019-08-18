module unary
  #(
    W_DATA = 16
    )
   (

    input                             clk,
    input                             rst,
    output wire                       din_ready,
    input wire                        din_valid,
    input wire [W_DATA-1:0]           din_data,

    input wire                        dout_ready,
    output wire                       dout_valid,
    output wire [(2**(W_DATA-1))-1:0] dout_data
    );

   assign dout_data  = unary(din_data);
   assign dout_valid = din_valid;
   assign din_ready  = dout_ready;

   function [(2**(W_DATA-1))-1 : 0] unary;
      input [W_DATA-1 : 0] binary;
      reg [(2**W_DATA)-1 : 0] unary_data;

      begin
         unary_data = 0;
         for (int i = 0; i < binary; i++) begin
            unary_data[i] = 1;
         end

         unary = unary_data;
      end
   endfunction

endmodule
