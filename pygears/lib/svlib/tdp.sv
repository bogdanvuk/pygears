module tdp
  #(
    W_DATA = 16,
    W_ADDR = 16,
    DEPTH = 1024
    )
   (
    input logic clk,
    input logic rst,
    dti.consumer req0,
    dti.consumer req1,

    dti.producer dout0,
    dti.producer dout1
    );

   logic        ena;
   logic        wea;
   logic [W_ADDR-1:0] addra;
   logic [W_DATA-1:0] dia;
   logic [W_DATA-1:0] doa;

   logic              enb;
   logic              web;
   logic [W_ADDR-1:0] addrb;
   logic [W_DATA-1:0] dib;
   logic [W_DATA-1:0] dob;

   tdp_port
     #(
       .W_DATA(W_DATA),
       .W_ADDR(W_ADDR)
       )
   port1
     (
      .clk(clk),
      .rst(rst),

      .req_if(req0),
      .data_if(dout0),

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

      .req_if(req1),
      .data_if(dout1),

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
      .*
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
    output logic [W_DATA-1:0] doa,

    input                     enb,
    input                     web,
    input [W_ADDR-1:0]        addrb,
    input [W_DATA-1:0]        dib,
    output logic [W_DATA-1:0] dob

    );

   logic [W_DATA-1:0]         ram [DEPTH-1:0];

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
    input               clk,
    input               rst,
                        dti.consumer req_if,
                        dti.producer data_if,
    // memory connections
    output              en_o,
    output              we_o,
    output [W_ADDR-1:0] addr_o,
    output [W_DATA-1:0] data_o,
    input  [W_DATA-1:0] data_i
    );

   typedef struct packed
   {
      logic [W_DATA-1:0] data;
      logic [W_ADDR-1:0] addr;
   } req_data_t;

   typedef struct packed
   {
      logic [0 : 0] ctrl;
      req_data_t    data;
   } req_t;

   req_t req_s;
   logic            rd_req_valid;
   logic            rd_req_empty;
   logic            rd_req_ready;

   assign req_s = req_if.data;

   assign rd_req_empty = !rd_req_valid;
   assign rd_req_ready = rd_req_empty || data_if.ready;

   // to memory
   assign addr_o = req_s.data.addr; // rd_req has addr at the same position
   assign data_o = req_s.data.data; // rd_req has no such field
   assign en_o = req_if.valid && rd_req_ready;
   assign we_o = en_o && req_s.ctrl;

   // address interface
   // assign req_if.ready = req_if.valid ? (req_s.ctrl ? 1'b1 : rd_req_ready) : 1'b1;
   assign req_if.ready = req_if.valid ? rd_req_ready : 1'b1;

   // data interface
   assign data_if.data  = data_i;
   assign data_if.valid = rd_req_valid;

   initial begin
      rd_req_valid = 1'b0;
   end

   // valid and eot for data interface are registered
   always @(posedge clk) begin
      if (rst) begin
         rd_req_valid <= 1'b0;
      end else if (rd_req_ready) begin
         rd_req_valid <= en_o && (!we_o);
      end
   end

endmodule
