
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

endinterface : dti


interface dti_spy #(
                type data_type = logic
                )(input spy_clk);

   data_type       data;
   logic           valid;
   logic           ready;
   logic           handshake;

   assign handshake = valid && ready && !spy_clk;

endinterface : dti_spy
