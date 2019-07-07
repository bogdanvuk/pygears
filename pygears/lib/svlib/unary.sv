module unary
  #(
    W_DATA = 16
    )
   (

    input clk,
    input rst,
    dti.consumer din,
    dti.producer dout
    );

   assign dout.data  = vu(din.data);
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

   function bit[(2**W_DATA)-1 : 0] vu (bit[W_DATA-1 : 0] din_bla);
      logic [(2**W_DATA)-1 : 0] vu_data;

      vu_data = 0;
      for (int i = 0; i < din_bla; i++) begin
         vu_data[i] = 1;
      end

      return vu_data;
   endfunction

endmodule
