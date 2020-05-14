module tdp
  #(
    W_DATA = 16,
    W_ADDR = 16,
    DEPTH = 1024
    )
   (
    input                        clk,
    input                        rst,

    output wire                  req0_ready,
    input wire                   req0_valid,
    input wire [W_DATA+W_ADDR:0] req0_data,

    output wire                  req1_ready,
    input wire                   req1_valid,
    input wire [W_DATA+W_ADDR:0] req1_data,

    input wire                   dout0_ready,
    output wire                  dout0_valid,
    output wire [W_DATA-1:0]     dout0_data,

    input wire                   dout1_ready,
    output wire                  dout1_valid,
    output wire [W_DATA-1:0]     dout1_data

    );

   wire        ena;
   wire        wea;
   wire [W_ADDR-1:0] addra;
   wire [W_DATA-1:0] dia;
   wire [W_DATA-1:0] doa;

   wire              enb;
   wire              web;
   wire [W_ADDR-1:0] addrb;
   wire [W_DATA-1:0] dib;
   wire [W_DATA-1:0] dob;

   tdp_port
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR)
       )
   port1
     (
      .clk(clk),
      .rst(rst),

      .req_if_data(req0_data),
      .req_if_ready(req0_ready),
      .req_if_valid(req0_valid),

      .data_if_data(dout0_data),
      .data_if_ready(dout0_ready),
      .data_if_valid(dout0_valid),

      .en_o(ena),
      .we_o(wea),
      .addr_o(addra),
      .data_o(dia),
      .data_i(doa)
      );

   tdp_port
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR)
       )
   port2
     (
      .clk(clk),
      .rst(rst),

      .req_if_data(req1_data),
      .req_if_ready(req1_ready),
      .req_if_valid(req1_valid),

      .data_if_data(dout1_data),
      .data_if_ready(dout1_ready),
      .data_if_valid(dout1_valid),

      .en_o(enb),
      .we_o(web),
      .addr_o(addrb),
      .data_o(dib),
      .data_i(dob)
      );

   tdp_mem
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR),
       .DEPTH(DEPTH)
       )
   m_ram
     (
      .clk(clk),
      .ena(ena),
      .wea(wea),
      .addra(addra),
      .dia(dia),
      .doa(doa),

      .enb(enb),
      .web(web),
      .addrb(addrb),
      .dib(dib),
      .dob(dob)
      );

endmodule

module tdp_mem #(
                 W_DATA = 16,
                 W_ADDR = 6,
                 DEPTH = 64
                 )
   (
    input                     clk,
    input                     ena,
    input                     wea,
    input [W_ADDR-1:0]        addra,
    input [W_DATA-1:0]        dia,
    output reg [W_DATA-1:0] doa,

    input                     enb,
    input                     web,
    input [W_ADDR-1:0]        addrb,
    input [W_DATA-1:0]        dib,
    output reg [W_DATA-1:0] dob

    );

   reg [W_DATA-1:0]         ram [DEPTH-1:0];

   always @(posedge clk) begin
      if (ena) begin
         if (wea) begin
            ram[addra] <= dia;
         end
         doa <= ram[addra];
      end
   end

   always @(posedge clk) begin
      if (enb) begin
         if (web) begin
            ram[addrb] <= dib;
         end
         dob <= ram[addrb];
      end
   end

endmodule


module tdp_port #(
                  W_DATA = 16,
                  W_ADDR = 16
                  )
   (
    input                        clk,
    input                        rst,

    output wire                  req_if_ready,
    input wire                   req_if_valid,
    input wire [W_DATA+W_ADDR:0] req_if_data,

    input wire                   data_if_ready,
    output wire                  data_if_valid,
    output wire [W_DATA-1:0]     data_if_data,

    // memory connections
    output                       en_o,
    output                       we_o,
    output [W_ADDR-1:0]          addr_o,
    output [W_DATA-1:0]          data_o,
    input [W_DATA-1:0]           data_i
    );

   wire [W_ADDR-1:0] req_s_data_addr;
   wire              req_s_ctrl;
   wire [W_DATA-1:0] req_s_data_data;

   reg              rd_req_valid;
   wire             rd_req_empty;
   wire             rd_req_ready;

   assign req_s_data_addr = req_if_data[W_ADDR-1:0];
   assign req_s_data_data = req_if_data[W_ADDR+W_DATA-1 : W_ADDR];
   assign req_s_ctrl = req_if_data[W_ADDR+W_DATA : W_ADDR+W_DATA];

   assign rd_req_empty = !rd_req_valid;
   assign rd_req_ready = rd_req_empty || data_if_ready;

   // to memory
   assign addr_o = req_s_data_addr; // rd_req has addr at the same position
   assign data_o = req_s_data_data; // rd_req has no such field
   assign en_o = req_if_valid && rd_req_ready;
   assign we_o = en_o && req_s_ctrl;

   // address interface
   assign req_if_ready = req_if_valid ? rd_req_ready : 1'b1;

   // data interface
   assign data_if_data  = data_i;
   assign data_if_valid = rd_req_valid;

   // valid and eot for data interface are registered
   always @(posedge clk) begin
      if (rst) begin
         rd_req_valid <= 1'b0;
      end else if (rd_req_ready) begin
         rd_req_valid <= en_o && (!we_o);
      end
   end

endmodule
