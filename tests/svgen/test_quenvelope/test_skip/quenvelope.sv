/*
    None
*/

module quenvelope
(
    input clk,
    input rst,
    dti.consumer din, // [u1]^5 (6)
    dti.producer dout // [()]^2 (2)

);
    typedef struct packed { // [u1]^5
        logic [1:0] out_eot; // u2
        logic [2:0] subenvelope; // u3
        logic [0:0] data; // u1
    } din_t;

    typedef struct packed { // [()]^2
        logic [1:0] out_eot; // u2
    } dout_t;


    din_t din_s;
    dout_t dout_s;

    assign din_s = din.data;


    assign dout_s.out_eot = din_s.out_eot;
    assign dout.data = dout_s;

    logic  handshake;
    logic  ready_reg;
    logic  valid_reg;
    logic  subelem_done;

    assign subelem_done = &din_s.subenvelope;
    assign din.ready = (dout.ready || ready_reg || (!subelem_done));
    assign dout.valid = (din.valid || valid_reg) && (!ready_reg);

    assign handshake = dout.valid & dout.ready;

    always_ff @(posedge clk) begin
        if (rst) begin
          ready_reg <= 1'b0;
          valid_reg <= 1'b0;
        end
        else begin
          if (subelem_done && handshake) begin
              ready_reg <= 1'b0;
              valid_reg <= 1'b0;
          end
          else begin
              ready_reg <= ready_reg || handshake;
              valid_reg <= valid_reg || din.valid;
          end
        end
    end


endmodule