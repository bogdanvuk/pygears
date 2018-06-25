
module sdp_wr_port #(
                     W_DATA = 16,
                     W_ADDR = 16
                     )
   (
    input                   clk,
    input                   rst,
    dti.consumer addr_data_if,
    // memory connections
    output                  en_o,
    output [W_ADDR-1:0] addr_o,
    output [W_DATA-1:0] data_o
    );

   typedef struct packed
                  {
                     logic [W_DATA-1:0] data;
                     logic [W_ADDR-1:0] addr;
                  } din_t;

   din_t addr_data_s;
   assign addr_data_s = addr_data_if.data;

   // to input
   assign addr_data_if.ready = 1'b1;

   // to memory
   assign data_o = addr_data_s.data;
   assign addr_o = addr_data_s.addr;
   assign en_o = addr_data_if.valid;

endmodule
