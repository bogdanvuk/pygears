module dynamic_sieve #(
               W_DATA = 16
               )
   (

    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout
    );

   typedef struct packed {
      logic [$clog2(W_DATA) : 0]      high_pos;
      logic [$clog2(W_DATA) : 0]      low_pos;
      logic [W_DATA-1:0]              data;
   } din_t;

   assign dout.eot    = din.eot;
   assign dout.data   = dyn_sieve(din.data);
   assign dout.dvalid = din.dvalid;
   assign din.dready  = dout.dready;

   function bit[W_DATA-1 : 0] dyn_sieve(din_t din);
      logic [W_DATA-1 : 0]              data;
      data = 0;
      for(int i = 0; i < W_DATA; i++)begin
         if ((i <= din.high_pos) && (din.low_pos <= i))
           data[i] = din.data[i];
      end
      return data;
   endfunction

	 // ---------------------------------------------------------------------------
	 // Usage checks
	 // ---------------------------------------------------------------------------

	 initial
	   if (($size(din.data) != W_DATA + 2*($clog2(W_DATA)+1)) | ($size(dout.data) != W_DATA))
	     $fatal(0, "Sieve incorrect usage: parameter and interface width mismatch");

endmodule : dynamic_sieve
