
module bc #(
            parameter SIZE=2,
            parameter WIDTH=16
            )
   (
    input                        clk,
    input                        rst,

    output wire                  din_ready,
    input wire                   din_valid,
    input wire [WIDTH-1:0]       din_data,

    input wire [SIZE-1:0]        dout_ready,
    output wire [SIZE-1:0]       dout_valid,
    output wire [WIDTH-1:0]      dout_data
    );

   reg [SIZE-1 : 0] ready_reg;
   wire [SIZE-1 : 0] ready_all;
   genvar           i;

   assign dout_data = din_data;

   initial begin
      ready_reg = 0;
   end

   generate
      for (i = 0; i < SIZE; i=i+1) begin
         reg others_ready;
         assign ready_all[i]  = dout_ready[i] | ready_reg[i];
         assign dout_valid[i] = din_valid & !ready_reg[i];

         always @* begin: others_calc
            reg [SIZE-1: 0] others_array;
            integer         j;

            for (j = 0; j < SIZE; j=j+1) begin
               if (j == i)
                 others_array[j] = 1;
               else
                 others_array[j] = ready_all[j];
            end

            others_ready = &others_array;
         end

         always @(posedge clk) begin
            if (ready_reg[i])
              ready_reg[i] = !(rst || others_ready);
            else
              ready_reg[i] = !rst && din_valid && (!din_ready) && dout_ready[i];
         end
      end
   endgenerate
   assign din_ready = &ready_all;

endmodule
