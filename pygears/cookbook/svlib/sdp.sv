
module sdp
  #(
    W_DATA = 16,
    W_ADDR = 16,
    DEPTH = 1024
    )
   (
    input clk,
    input rst,
    dti.consumer wr_addr_data_if,
    dti.consumer rd_addr_if,
    dti.producer rd_data_if
    );

   logic  wr_en_s;
   logic [W_ADDR-1:0] wr_addr_s;
   logic [W_DATA-1:0] wr_data_s;
   logic                  rd_en_s;
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
      .addr_data_if(wr_addr_data_if),
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
      .addr_if(rd_addr_if),
      .data_if(rd_data_if),
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
