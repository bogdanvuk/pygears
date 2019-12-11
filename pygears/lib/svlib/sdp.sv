
module sdp
  #(
    W_DATA = 16,
    W_ADDR = 16,
    DEPTH = 1024
    )
   (
    input logic clk,
    input logic rst,
    dti.consumer wr_addr_data,
    dti.consumer rd_addr,
    dti.producer rd_data
    );

   logic  wr_en_s;
   logic [W_ADDR-1:0] wr_addr_s;
   logic [W_DATA-1:0] wr_data_s;
   logic              rd_en_s;
   logic [W_ADDR-1:0] rd_addr_s;
   logic [W_DATA-1:0] rd_data_s;

   sdp_wr_port
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR)
       )
   m_wr_port
     (
      .clk(clk),
      .rst(rst),
      .addr_data_if(wr_addr_data),
      .en_o(wr_en_s),
      .addr_o(wr_addr_s),
      .data_o(wr_data_s)
      );

   sdp_rd_port
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR)
       )
   m_rd_port
     (
      .clk(clk),
      .rst(rst),
      .addr_if(rd_addr),
      .data_if(rd_data),
      .en_o(rd_en_s),
      .addr_o(rd_addr_s),
      .data_i(rd_data_s)
      );

   sdp_mem
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR),
       .DEPTH(DEPTH)
       )
   m_ram
     (
      .clk(clk),
      .ena(wr_en_s),
      .enb(rd_en_s),
      .wea(wr_en_s),
      .addra(wr_addr_s),
      .addrb(rd_addr_s),
      .dia(wr_data_s),
      .dob(rd_data_s)
      );

endmodule

module sdp_mem #(
                 W_DATA = 16,
                 W_ADDR = 6,
                 DEPTH = 64
                 )
   (
    input                     clk,
    input                     ena, // primary global enable
    input                     enb, // dual global enable
    input                     wea, // primary write enable
    input [W_ADDR-1:0]        addra, // write address / primary read address
    input [W_ADDR-1:0]        addrb, // dual read address
    input [W_DATA-1:0]        dia, // primary data input
    output logic [W_DATA-1:0] dob    //dual output port
    );

   logic [W_DATA-1:0]         ram [DEPTH-1:0];

   always @(posedge clk) begin
      if (ena) begin
         if (wea) begin
            ram[addra] <= dia;
         end
      end
   end

   always @(posedge clk) begin
      if (enb) begin
         dob <= ram[addrb];
      end
   end

endmodule


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
   always @(posedge clk) begin
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

module sdp_wr_port #(
                     W_DATA = 16,
                     W_ADDR = 16
                     )
   (
    input               clk,
    input               rst,
                        dti.consumer addr_data_if,
    // memory connections
    output              en_o,
    output [W_ADDR-1:0] addr_o,
    output [W_DATA-1:0] data_o
    );

   typedef struct       packed
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
