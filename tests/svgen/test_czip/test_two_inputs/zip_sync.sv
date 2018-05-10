
module zip_sync
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

      dti #(.W_DATA(6)) din0_if(); // [u3]^3 (6)
      dti #(.W_DATA(9)) din1_if(); // [u4]^5 (9)

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

    assign dout0_if.valid = out_valid;
    assign dout0_if.data = din0_s;
    assign din0.ready = all_valid && (dout0_if.ready || !din0_eot_aligned);
    assign dout1_if.valid = out_valid;
    assign dout1_if.data = din1_s;
    assign din1.ready = all_valid && (dout1_if.ready || !din1_eot_aligned);


    zip_sync_syncguard syncguard (
        .clk(clk),
        .rst(rst),
        .din0(din0_if),
        .din1(din1_if),
        .dout0(dout0),
        .dout1(dout1)
    );


endmodule