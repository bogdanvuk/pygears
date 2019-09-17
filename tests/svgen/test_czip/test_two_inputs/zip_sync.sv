module zip_sync_base
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // [u4]^5 (9)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // [u4]^5 (9)

);
    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din0_t;

    typedef struct packed { // [u4]^5
        logic [4:0] eot; // u5
        logic [3:0] data; // u4
    } din1_t;

    din0_t din0_s;
    din1_t din1_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;


    logic all_valid;
    logic out_valid;
    logic out_ready;
    logic all_aligned;
    logic handshake;
    logic [2:0] din0_eot_overlap;
    logic din0_eot_aligned;
    logic [2:0] din1_eot_overlap;
    logic din1_eot_aligned;

    assign din0_eot_overlap = din0_s.eot[2:0];
    assign din1_eot_overlap = din1_s.eot[2:0];
    assign din0_eot_aligned = din0_eot_overlap >= din1_eot_overlap;
    assign din1_eot_aligned = din1_eot_overlap >= din0_eot_overlap;

    assign all_valid   = din0.valid && din1.valid;
    assign all_aligned = din0_eot_aligned && din1_eot_aligned;
    assign out_valid   = all_valid & all_aligned;

    assign dout0.valid = out_valid;
    assign dout0.data = din0_s;
    assign din0.ready = all_valid && (dout0.ready || !din0_eot_aligned);
    assign dout1.valid = out_valid;
    assign dout1.data = din1_s;
    assign din1.ready = all_valid && (dout1.ready || !din1_eot_aligned);



endmodule



module zip_sync_syncguard
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.producer dout0, // [u3]^3 (6)
    dti.consumer din1, // [u4]^5 (9)
    dti.producer dout1 // [u4]^5 (9)

);


    localparam SIZE = 2;

    logic in_valid;
    logic in_ready;
    logic [SIZE-1 : 0] out_valid;
    logic [SIZE-1 : 0] out_ready;
    logic [SIZE-1 : 0] ready_reg;
    logic [SIZE-1 : 0] ready_all;

    assign in_valid = din0.valid && din1.valid;
    assign out_ready = { dout1.ready, dout0.ready };
    assign in_ready = &ready_all;

    assign din0.ready = in_ready;
    assign dout0.valid = out_valid[0];
    assign dout0.data = din0.data;
    assign din1.ready = in_ready;
    assign dout1.valid = out_valid[1];
    assign dout1.data = din1.data;

   initial begin
      ready_reg = 0;
   end

   generate
      for (genvar i = 0; i < SIZE; i++) begin
         assign ready_all[i]  = out_ready[i] || ready_reg[i];
         assign out_valid[i]  = in_valid && !ready_reg[i];

         always @(posedge clk) begin
            if (rst || (!in_valid) || in_ready) begin
               ready_reg[i] <= 1'b0;
            end else if (out_ready[i]) begin
               ready_reg[i] <= 1'b1;
            end
         end
      end
   endgenerate


endmodule


module zip_sync
(
    input clk,
    input rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // [u4]^5 (9)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // [u4]^5 (9)

);

        dti #(.W_DATA(6)) dout0_if(); // [u3]^3 (6)
        dti #(.W_DATA(9)) dout1_if(); // [u4]^5 (9)




      zip_sync_base base (
        .clk(clk),
        .rst(rst),
        .din0(din0),
        .din1(din1),
        .dout0(dout0_if),
        .dout1(dout1_if)
    );

      zip_sync_syncguard syncguard (
        .clk(clk),
        .rst(rst),
        .din0(dout0_if),
        .dout0(dout0),
        .din1(dout1_if),
        .dout1(dout1)
    );


endmodule
