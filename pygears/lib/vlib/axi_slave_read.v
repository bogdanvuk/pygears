////////////////////////////////////////////////////////////////////////////////
//
// Filename: 	axi2axilite.v
//
// Project:	WB2AXIPSP: bus bridges and other odds and ends
//
// Purpose:	Convert from AXI to AXI-lite
//
// Performance: 
//
// Creator:	Dan Gisselquist, Ph.D.
//		Gisselquist Technology, LLC
//
////////////////////////////////////////////////////////////////////////////////
//
// Copyright (C) 2019-2020, Gisselquist Technology, LLC
//
// This file is part of the WB2AXIP project.
//
// The WB2AXIP project contains free software and gateware, licensed under the
// Apache License, Version 2.0 (the "License").  You may not use this project,
// or this file, except in compliance with the License.  You may obtain a copy
// of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
// License for the specific language governing permissions and limitations
// under the License.
//
////////////////////////////////////////////////////////////////////////////////
//
//
`default_nettype	none
//
(* dont_touch = "yes", mark_debug = "yes" *)
module axi_slave_read #(
	parameter integer C_AXI_ID_WIDTH	= 2,
	parameter integer C_AXI_DATA_WIDTH	= 32,
	parameter integer C_AXI_ADDR_WIDTH	= 6,
	parameter	 [0:0]	OPT_READS	= 1,
	// Log (based two) of the maximum number of outstanding AXI
	// (not AXI-lite) transactions.  If you multiply 2^LGFIFO * 256,
	// you'll get the maximum number of outstanding AXI-lite transactions
	parameter	LGFIFO			= 4
	) (
		input	wire	S_AXI_ACLK,
		input	wire	S_AXI_ARESETN,
		//
		input	wire				S_AXI_ARVALID,
		output	wire				S_AXI_ARREADY,
		input	wire	[C_AXI_ID_WIDTH-1:0]	S_AXI_ARID,
		input	wire	[C_AXI_ADDR_WIDTH-1:0]	S_AXI_ARADDR,
		input	wire	[7:0]			S_AXI_ARLEN,
		input	wire	[2:0]			S_AXI_ARSIZE,
		input	wire	[1:0]			S_AXI_ARBURST,
		input	wire				S_AXI_ARLOCK,
		input	wire	[3:0]			S_AXI_ARCACHE,
		input	wire	[2:0]			S_AXI_ARPROT,
		input	wire	[3:0]			S_AXI_ARQOS,
		//
		output	wire				S_AXI_RVALID,
		input	wire				S_AXI_RREADY,
		output	wire	[C_AXI_ID_WIDTH-1:0] S_AXI_RID,
		output	wire	[C_AXI_DATA_WIDTH-1:0] S_AXI_RDATA,
		output	wire	[1:0]			S_AXI_RRESP,
		output	wire				S_AXI_RLAST,
		//
		//
		//
		// Write address (issued by master, acceped by Slave)
		output	wire	[C_AXI_ADDR_WIDTH-1:0]	M_AXI_ARADDR,
		output	wire	[2:0]			M_AXI_ARPROT,
		output	wire				M_AXI_ARVALID,
		input	wire				M_AXI_ARREADY,
		//
		input	wire				M_AXI_RVALID,
		output	wire				M_AXI_RREADY,
		input	wire	[C_AXI_DATA_WIDTH-1 : 0] M_AXI_RDATA,
		input	wire	[1 : 0]			M_AXI_RRESP
	);

	localparam [1:0]	OKAY = 2'b00,
				EXOKAY = 2'b01,
				SLVERR = 2'b10,
				DECERR = 2'b10;
	localparam	AW = C_AXI_ADDR_WIDTH;
	localparam	DW = C_AXI_DATA_WIDTH;
	localparam	IW = C_AXI_ID_WIDTH;
	localparam	LSB = $clog2(C_AXI_DATA_WIDTH)-3;


	// Read register
	(* dont_touch = "yes", mark_debug = "yes" *) reg				m_axi_arvalid;
	(* dont_touch = "yes", mark_debug = "yes" *) wire	[4:0]			rfifo_count;
	(* dont_touch = "yes", mark_debug = "yes" *) wire				rfifo_full;
	 (* dont_touch = "yes", mark_debug = "yes" *) wire				rfifo_empty;
	 (* dont_touch = "yes", mark_debug = "yes" *) wire	[7:0]			rfifo_rcount;
	 (* dont_touch = "yes", mark_debug = "yes" *) reg				s_axi_rvalid;
	 (* dont_touch = "yes", mark_debug = "yes" *) reg	[1:0]			s_axi_rresp;
	 (* dont_touch = "yes", mark_debug = "yes" *) reg	[8:0]			rcounts;
	 (* dont_touch = "yes", mark_debug = "yes" *) reg	[C_AXI_ADDR_WIDTH-1:0]	axi_araddr;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[7:0]			axi_arlen, axi_rlen;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[1:0]			axi_arburst;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[2:0]			axi_arsize;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[C_AXI_ADDR_WIDTH-1:0]	next_read_addr;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[C_AXI_ID_WIDTH-1:0]	s_axi_rid;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[C_AXI_ID_WIDTH-1:0]	rfifo_rid;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[C_AXI_DATA_WIDTH-1:0]	s_axi_rdata;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg				s_axi_rlast;
	 (* dont_touch = "yes", mark_debug = "yes" *)reg	[IW-1:0]		rid;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire				read_from_rdfifo;

	//
	// S_AXI_AR* skid buffer
   (* dont_touch = "yes", mark_debug = "yes" *)	wire			skids_arvalid, skids_arready;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[IW-1:0]	skids_arid;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[AW-1:0]	skids_araddr;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[7:0]		skids_arlen;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[2:0]		skids_arsize;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[1:0]		skids_arburst;
	//
	// S_AXI_R* skid buffer isn't needed
	//
	// M_AXI_AR* skid buffer isn't needed
	// M_AXI_R* skid buffer
	 (* dont_touch = "yes", mark_debug = "yes" *)wire			skidm_rvalid, skidm_rready;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[DW-1:0]	skidm_rdata;
	 (* dont_touch = "yes", mark_debug = "yes" *)wire	[1:0]		skidm_rresp;

   (* dont_touch = "yes", mark_debug = "yes" *) wire addr_req;
   (* dont_touch = "yes", mark_debug = "yes" *) wire rdata_handshake;
   (* dont_touch = "yes", mark_debug = "yes" *) wire araddr_handshake;

	////////////////////////////////////////////////////////////////////////
	//
	// Read half
	//
	generate if (OPT_READS)
	begin
		//
		// S_AXI_AR* skid buffer
		skidbuffer #(.DW(IW+AW+8+3+2), .OPT_LOWPOWER(0), .OPT_OUTREG(0))
		arskid(S_AXI_ACLK, !S_AXI_ARESETN,
			S_AXI_ARVALID, S_AXI_ARREADY,
			{ S_AXI_ARID, S_AXI_ARADDR, S_AXI_ARLEN, S_AXI_ARSIZE,
				S_AXI_ARBURST },
			skids_arvalid, skids_arready,
			{ skids_arid, skids_araddr, skids_arlen, skids_arsize,
				skids_arburst });
		//
		// M_AXI_R* skid buffer
		skidbuffer #(.DW(DW+2), .OPT_LOWPOWER(0), .OPT_OUTREG(0))
		rskid(S_AXI_ACLK, !S_AXI_ARESETN,
			    M_AXI_RVALID, M_AXI_RREADY, { M_AXI_RDATA, M_AXI_RRESP },
			skidm_rvalid, skidm_rready, { skidm_rdata, skidm_rresp });

		initial	m_axi_arvalid = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			m_axi_arvalid <= 0;
		else if (araddr_handshake)
			m_axi_arvalid <= 1;
		else if (M_AXI_ARREADY && axi_arlen == 0)
			m_axi_arvalid <= 0;

		always @(posedge S_AXI_ACLK)
		if (araddr_handshake)
		begin
			axi_araddr  <= skids_araddr;
			axi_arburst <= skids_arburst;
			axi_arsize  <= skids_arsize;
			axi_rlen    <= skids_arlen;
		end else if (M_AXI_ARREADY)
			axi_araddr <= next_read_addr;

		axi_addr #(.AW(C_AXI_ADDR_WIDTH))
			calcrdaddr(axi_araddr, axi_arsize, axi_arburst,
			axi_rlen, next_read_addr);


		initial	axi_arlen = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			axi_arlen <= 0;
		else if (araddr_handshake)
			axi_arlen <= skids_arlen;
		else if (M_AXI_ARVALID && M_AXI_ARREADY && axi_arlen > 0)
			axi_arlen <= axi_arlen - 1;

		assign	skids_arready = (!M_AXI_ARVALID ||
				((axi_arlen == 0) && M_AXI_ARREADY))
				&& !rfifo_full;

    assign rdata_handshake = skidm_rvalid && skidm_rready;
    assign araddr_handshake = skids_arvalid && skids_arready;
		assign read_from_rdfifo = rdata_handshake && (rcounts <= 1) && !rfifo_empty;

		sfifo	#(.BW(C_AXI_ID_WIDTH+8), .LGFLEN(LGFIFO))
		ridlnfifo(S_AXI_ACLK, !S_AXI_ARESETN,
			araddr_handshake,
			{ skids_arid, skids_arlen },
			rfifo_full, rfifo_count,
			read_from_rdfifo,
			{ rfifo_rid, rfifo_rcount }, rfifo_empty);


     assign addr_req = m_axi_arvalid || (araddr_handshake);
		 // assign	skidm_rready = (!S_AXI_RVALID || S_AXI_RREADY) && addr_req;
		 assign	skidm_rready = (!S_AXI_RVALID || S_AXI_RREADY) && !rfifo_empty;

		initial	s_axi_rvalid = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			s_axi_rvalid <= 0;
		else if (rdata_handshake)
			s_axi_rvalid <= 1;
		else if (S_AXI_RREADY)
			s_axi_rvalid <= 0;

		always @(posedge S_AXI_ACLK)
		if (rdata_handshake)
		begin
			s_axi_rresp <= skidm_rresp;
			s_axi_rdata <= skidm_rdata;
		end else if (S_AXI_RREADY)
		begin
			s_axi_rresp <= 0;
			s_axi_rdata <= 0;
		end

		// Return counts
		initial	rcounts = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			rcounts <= 0;
		else if (read_from_rdfifo)
			rcounts <= rcounts + rfifo_rcount;
		else if (rdata_handshake)
			rcounts <= rcounts - 1;

		initial	rid = 0;
		always @(posedge S_AXI_ACLK)
		if (read_from_rdfifo)
			rid <= rfifo_rid;

		always @(posedge S_AXI_ACLK)
		if (!S_AXI_RVALID || S_AXI_RREADY)
		begin
			// if (rcounts == 1) s_axi_rlast <= 1; else
			if (read_from_rdfifo)
				s_axi_rlast <= (rfifo_rcount == 0);
			else
				s_axi_rlast <= 0;

			if (rcounts == 1)
				s_axi_rlast <= 1;
		end

		initial	s_axi_rid = 0;
		always @(posedge S_AXI_ACLK)
		if ((S_AXI_RVALID && S_AXI_RREADY && S_AXI_RLAST)
				||(!S_AXI_RVALID && rcounts == 0))
			s_axi_rid <= (read_from_rdfifo)&&(rcounts == 0)?rfifo_rid : rid;

		assign	M_AXI_ARVALID= m_axi_arvalid;
		assign	M_AXI_ARADDR = axi_araddr;
		assign	M_AXI_ARPROT = 0;
		assign	S_AXI_RVALID = s_axi_rvalid;
		assign	S_AXI_RDATA  = s_axi_rdata;
		assign	S_AXI_RRESP  = s_axi_rresp;
		assign	S_AXI_RLAST  = s_axi_rlast;
		assign	S_AXI_RID    = s_axi_rid;

	end else begin // if (!OPT_READS)
		assign	M_AXI_ARVALID= 0;
		assign	M_AXI_ARADDR = 0;
		assign	M_AXI_ARPROT = 0;
		assign	M_AXI_RREADY = 0;
		//
		assign	S_AXI_ARREADY= 0;
		assign	S_AXI_RVALID = 0;
		assign	S_AXI_RDATA  = 0;
		assign	S_AXI_RRESP  = 0;
		assign	S_AXI_RLAST  = 0;
		assign	S_AXI_RID    = 0;

		//
		assign	skids_arvalid = S_AXI_ARVALID;
		assign	skids_arready = S_AXI_ARREADY;
		assign	skids_arid    = S_AXI_ARID;
		assign	skids_araddr  = S_AXI_ARADDR;
		assign	skids_arlen   = S_AXI_ARLEN;
		assign	skids_arsize  = S_AXI_ARSIZE;
		assign	skids_arburst = S_AXI_ARBURST;
		//
		assign	skidm_rvalid  = M_AXI_RVALID;
		assign	skidm_rready  = M_AXI_RREADY;
		assign	skidm_rdata   = M_AXI_RDATA;
		assign	skidm_rresp   = M_AXI_RRESP;
		//
		//
		always @(*)
		begin
			axi_arlen = 0;

			rcounts = 0;
			rid = 0;

		end
		assign	rfifo_empty = 1;
		assign	rfifo_full  = 0;
		assign	rfifo_count = 0;

	end endgenerate

	// Verilator lint_off UNUSED
	wire	[35-1:0]	unused;
	assign	unused = {
		S_AXI_ARLOCK, S_AXI_ARCACHE, S_AXI_ARPROT, S_AXI_ARQOS,
		rfifo_count };
	// Verilator lint_on  UNUSED

endmodule
`ifndef	YOSYS
`default_nettype wire
`endif
