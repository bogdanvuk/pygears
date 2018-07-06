`ifndef QENVELOPE_SV
`define QENVELOPE_SV

class qenvelope #(int lvl=1);

   rand int data_size;
   rand int num_trans[lvl][$];

   bit [lvl-1 : 0] eots[$];
   bit [lvl-1 : 0] res;
   int idx;

   constraint c_data_size {soft data_size inside {[1 : 1024]};}

   constraint c_trans_split {
      foreach (num_trans[i,j])
         num_trans[i][j] inside {[1:data_size]};
   }

   constraint c_trans_consistent_cnt {
      foreach (num_trans[i]) {
         if (i == lvl-1) {
            num_trans[i].size == 1;
         } else if (i == 0) {
            num_trans[i].size inside {[1:data_size]};
            soft num_trans[i].size <= 10;
         } else {
            num_trans[i].size inside {[1:num_trans[i-1].size]};
         }

         if (i==0) {
            num_trans[i].sum() == data_size;
         } else {
            num_trans[i].sum() == num_trans[i-1].size();
         }
      }
   }

   function void eot_setup(int cur_lvl, bit [lvl-1:0] eot, int trans_id);
      int flat_subtrans_id;

      for (int sub_trans_id = 0; sub_trans_id < num_trans[cur_lvl][trans_id]; sub_trans_id++) begin
         if (sub_trans_id == num_trans[cur_lvl][trans_id] - 1) begin
            eot[cur_lvl] = 1;
         end else begin
            eot[cur_lvl] = 0;
         end

         flat_subtrans_id = sub_trans_id;
         for (int i = 0; i < trans_id; i++)
           flat_subtrans_id += num_trans[cur_lvl][i];

         if (cur_lvl == 0) begin
            this.eots[flat_subtrans_id] = eot;
         end else begin
            eot_setup(cur_lvl - 1, eot, flat_subtrans_id);
         end

         flat_subtrans_id++;
      end
   endfunction

   function void post_randomize();
      if (idx == 0) eot_setup(lvl-1, {lvl{1'b0}}, 0);
      res = eots[idx];
      idx++;
      data_size.rand_mode(0);
      if (idx == data_size) begin
         data_size.rand_mode(1);
         idx = 0;
         this.eots = {};
      end
   endfunction

endclass

`endif
