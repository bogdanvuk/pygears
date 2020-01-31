module zip_sync
(
    input logic clk,
    input logic rst,
    dti.consumer din0, // [u3]^3 (6)
    dti.consumer din1, // u4 (4)
    dti.producer dout0, // [u3]^3 (6)
    dti.producer dout1 // u4 (4)

);
    typedef struct packed { // [u3]^3
        logic [2:0] eot; // u3
        logic [2:0] data; // u3
    } din0_t;

    typedef logic [3:0] din1_t; // u4

    din0_t din0_s;
    din1_t din1_s;
    assign din0_s = din0.data;
    assign din1_s = din1.data;


    logic all_aligned;
    logic handshake;
    logic din0_eot_aligned;
    logic din1_eot_aligned;

    assign din0_eot_aligned = 1;
    assign din1_eot_aligned = 1;

    assign all_aligned = din0_eot_aligned && din1_eot_aligned;

    assign dout0.valid = din0.valid & all_aligned;
    assign dout0.data = din0_s;
    assign din0.ready = din0.valid && (dout0.ready || !din0_eot_aligned);
    assign dout1.valid = din1.valid & all_aligned;
    assign dout1.data = din1_s;
    assign din1.ready = din1.valid && (dout1.ready || !din1_eot_aligned);



endmodule
