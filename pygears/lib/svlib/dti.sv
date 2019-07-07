
interface dti #(
                W_DATA = 64
                )();

   logic [W_DATA-1:0] data;
   logic              valid;
   logic              ready;

   // -------------------------------------------------------------------------
   // modports
   // -------------------------------------------------------------------------
   modport producer (output data,
                     output valid,
                     input  ready);
   modport consumer (input  data,
                     input  valid,
                     output ready);

endinterface
