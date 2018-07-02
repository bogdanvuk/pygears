
module sdp_rd_port #(
                     W_DATA = 16,
                     W_ADDR = 16
                     )
   (
    input                   clk,
    input                   rst,
                            dti.consumer addr_if,
                            dti.producer data_if,
    // memory connections
    output                  en_o,
    output [W_ADDR-1:0] addr_o,
    input [W_DATA-1:0]  data_i
    );

   logic                    data_dvalid_reg;
   logic                    is_empty;
   assign is_empty = !(data_dvalid_reg & !data_if.ready);

   // to memory
   assign addr_o = addr_if.data;
   assign en_o = addr_if.valid & is_empty;

   // address interface
   assign addr_if.ready = is_empty;

   // data interface
   assign data_if.data   = data_i;
   assign data_if.valid = data_dvalid_reg;

   // valid and eot for data interface are registered
   always_ff @(posedge clk) begin
      if (rst) begin
         data_dvalid_reg <= 1'b0;
      end
      else begin
         if (is_empty) begin
            data_dvalid_reg <= en_o;
         end
      end
   end

endmodule
