`define `maybe_signed(val) (SIGNED ? signed'(val) : val)

module rnggen
  #(
    parameter W_INCR = 16,
    parameter W_CNT  = 16,
    parameter W_START = 16,
    parameter CNT_STEPS = 0,
    parameter INCR_STEPS = 0,
    parameter CNT_ONE_MORE = 0,
    parameter SIGNED = 0
    )
   (
    input clk,
    input rst,
    dti_s_if.consumer cfg,
    dti_s_if.producer dout
    );

   typedef struct packed
                  {
                     logic [W_INCR-1 : 0] incr;
                     logic [W_CNT-1 : 0]  cnt;
                     logic [W_START-1:0]  base;
                  } cfg_t;

   typedef struct packed
                  {
                     logic eot;
                     logic [$size(dout.data)-2:0] data;
                  } dout_t;

   cfg_t cfg_s;
   dout_t dout_s;
   logic [W_CNT-1:0] 							  cnt_next;
   logic [W_CNT-1:0] 							  cnt_reg;

   logic 										  eot_internal_cond;
   logic 										  handshake;

   assign cfg_s = cfg.data;
   assign dout.data = dout_s;

   assign dout.dvalid = cfg.dvalid;
   assign cfg.dready = eot_internal_cond & handshake;
   assign dout.eot = 0;

   assign dout_s.eot = eot_internal_cond;

   if (CNT_STEPS) begin
	  if (INCR_STEPS) begin
		 assign dout_s.data = `maybe_signed(cfg_s.base)
		   + cnt_reg*`maybe_signed(cfg_s.incr);
		 assign cnt_next = cnt_reg + 1;
	  end else begin
		 assign dout_s.data = `maybe_signed(cfg_s.base) + `maybe_signed(cnt_reg);
		 assign cnt_next = cnt_reg + cfg_s.incr;
	  end
   end else begin
      logic cnt_started;

      always_ff @(posedge clk) begin
         if (rst | (eot_internal_cond & handshake)) begin
            cnt_started <= 1'b0;
         end else if (handshake) begin
            cnt_started <= 1'b1;
         end
      end

      assign dout_s.data = cnt_started ? cnt_reg : cfg_s.base;
      assign cnt_next = `maybe_signed(dout_s.data) + `maybe_signed(cfg_s.incr);
   end

   if (CNT_ONE_MORE || (!CNT_STEPS))
     assign eot_internal_cond = (cnt_reg == cfg_s.cnt);
   else
     assign eot_internal_cond = (cnt_next == cfg_s.cnt);

   assign handshake = dout.dready & cfg.dvalid;

   always_ff@(posedge clk) begin
      if (rst | (eot_internal_cond & handshake)) begin
         cnt_reg <= '0;
      end else if (handshake) begin
         cnt_reg <= cnt_next;
      end
   end

   // ---------------------------------------------------------------------------
   // Usage checks
   // ---------------------------------------------------------------------------

   initial begin
      asrt_input_width : assert (W_INCR + W_CNT + W_START == $size(cfg.data))
        else begin
           $display("Interface width and parameter mismatch");
           $fatal(0);
        end
   end

   if (CNT_ONE_MORE == 0) begin
      asrt_nonzero_cnt : assert property (
                                          @(posedge clk) disable iff(rst)
                                          cfg.dvalid |-> cfg_s.cnt !== 0)
        else $error("Empty list not supported when CNT_ONE_MORE == 0.");
   end

endmodule
