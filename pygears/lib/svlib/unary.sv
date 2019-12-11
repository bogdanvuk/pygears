module unary
  #(
    W_DATA = 16
    )
   (

    input logic clk,
    input logic rst,
    dti.consumer din,
    dti.producer dout
    );

   assign dout.data  = unary(din.data);
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

   function bit[(2**(W_DATA-1))-1 : 0] unary (bit[W_DATA-1 : 0] binary);
      logic [(2**W_DATA)-1 : 0] unary_data;

      unary_data = 0;
      for (int i = 0; i < binary; i++) begin
         unary_data[i] = 1;
      end

      return unary_data;
   endfunction

endmodule
