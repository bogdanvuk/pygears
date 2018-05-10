
module zip_sync_syncguard
(
    input clk,
    input rst,
    dti.consumer din0, //  ()
    dti.producer dout0, //  ()
    dti.consumer din1, //  ()
    dti.producer dout1 //  ()

);

    localparam SIZE = 2;

    logic in_ready;
    logic [SIZE-1 : 0] channel_open_reg;
    logic [SIZE-1 : 0] ready_all;

    logic [SIZE-1 : 0] out_valid;
    logic [SIZE-1 : 0] out_ready;

    logic [SIZE-1 : 0] in_valid;

    logic [SIZE-1 : 0] channel_open;


    assign in_valid = { din1.valid, din0.valid };
    assign din0.ready = in_ready;
    assign din1.ready = in_ready;

    assign out_ready = { dout1.ready, dout0.ready };

    assign dout0.valid = out_valid[0];
    assign dout0.data = din0.data;
    assign dout1.valid = out_valid[1];
    assign dout1.data = din1.data;

    assign in_ready = &ready_all;
    generate
        for (genvar i = 0; i < SIZE; i++) begin
         // Since data has been posted, i-th channel is considered to have been
         // opened if either
         assign channel_open[i]
           = channel_open_reg[i] | // i-th channel has already been opened any time
             // since the data has been posted
             out_ready[i];   // or, i-th consumer is currently ready

         // For each channel the data is considered consumed, if either:
         assign ready_all[i]
           = channel_open[i] |            // the channel has been open
             ~(in_valid[i]);  // or, no data has been output to the channel

         // Block valid signal if channel has been opened any time
         // since the data has been posted
         assign out_valid[i] = in_valid[i] & !channel_open_reg[i];

         always_ff @(posedge clk) begin
            if (rst | in_ready) begin
               channel_open_reg[i] <= 1'b0;
            end
            else begin
               channel_open_reg[i] <= channel_open[i];
            end
         end
      end
   endgenerate

endmodule