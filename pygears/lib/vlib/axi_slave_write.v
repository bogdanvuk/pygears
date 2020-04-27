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
(* dont_touch = "yes" *)
module axi_slave_write #(
	parameter integer C_AXI_ID_WIDTH	= 2,
	parameter integer C_AXI_DATA_WIDTH	= 32,
	parameter integer C_AXI_ADDR_WIDTH	= 6,
	parameter	 [0:0]	OPT_WRITES	= 1,
	// Log (based two) of the maximum number of outstanding AXI
	// (not AXI-lite) transactions.  If you multiply 2^LGFIFO * 256,
	// you'll get the maximum number of outstanding AXI-lite transactions
	parameter	LGFIFO			= 4
	) (
		input wire                               S_AXI_ACLK,
		input wire                               S_AXI_ARESETN,
		//
		input wire                               S_AXI_AWVALID,
		output wire                              S_AXI_AWREADY,
		input wire [C_AXI_ID_WIDTH-1:0]        S_AXI_AWID,
		input wire [C_AXI_ADDR_WIDTH-1:0]      S_AXI_AWADDR,
		input wire [7:0]                         S_AXI_AWLEN,
		input wire [2:0]                         S_AXI_AWSIZE,
		input wire [1:0]                         S_AXI_AWBURST,
		input wire                               S_AXI_AWLOCK,
		input wire [3:0]                         S_AXI_AWCACHE,
		input wire [2:0]                         S_AXI_AWPROT,
		input wire [3:0]                         S_AXI_AWQOS,
		//
		input wire                               S_AXI_WVALID,
		output wire                              S_AXI_WREADY,
		input wire [C_AXI_DATA_WIDTH-1:0]      S_AXI_WDATA,
		input wire [(C_AXI_DATA_WIDTH/8)-1:0]  S_AXI_WSTRB,
		input wire                               S_AXI_WLAST,
		//
		output wire                              S_AXI_BVALID,
		input wire                               S_AXI_BREADY,
		output wire [C_AXI_ID_WIDTH-1:0]       S_AXI_BID,
		output wire [1:0]                        S_AXI_BRESP,
		//
		//
		// Write address (issued by master, acceped by Slave)
		output wire [C_AXI_ADDR_WIDTH-1:0]     M_AXI_AWADDR,
		output wire [2 : 0]                      M_AXI_AWPROT,
		output wire                              M_AXI_AWVALID,
		input wire                               M_AXI_AWREADY,
		output wire [C_AXI_DATA_WIDTH-1:0]     M_AXI_WDATA,
		output wire [(C_AXI_DATA_WIDTH/8)-1:0] M_AXI_WSTRB,
		output wire                              M_AXI_WVALID,
		input wire                               M_AXI_WREADY,
		input wire [1 : 0]                       M_AXI_BRESP,
		input wire                               M_AXI_BVALID,
		output wire                              M_AXI_BREADY
	);

	localparam [1:0]	OKAY = 2'b00,
				EXOKAY = 2'b01,
				SLVERR = 2'b10,
				DECERR = 2'b10;
	localparam	AW = C_AXI_ADDR_WIDTH;
	localparam	DW = C_AXI_DATA_WIDTH;
	localparam	IW = C_AXI_ID_WIDTH;
	localparam	LSB = $clog2(C_AXI_DATA_WIDTH)-3;


	//
	// Write registers
	reg				m_axi_awvalid, s_axi_wready;
	reg	[C_AXI_ADDR_WIDTH-1:0]	axi_awaddr;
	reg	[7:0]			axi_awlen, axi_blen;
	reg	[1:0]			axi_awburst;
	reg	[2:0]			axi_awsize;
	wire	[C_AXI_ADDR_WIDTH-1:0]	next_write_addr;
	wire	[4:0]			wfifo_count;
	wire				wfifo_full;
	wire				wfifo_empty;
	wire	[7:0]			wfifo_bcount;
	wire	[IW-1:0]		wfifo_bid;
	reg	[8:0]			bcounts;
	reg	[C_AXI_ID_WIDTH-1:0]	axi_bid, bid;
	reg	[1:0]			axi_bresp;
	reg				s_axi_bvalid;
	wire				read_from_wrfifo;

	//
	// S_AXI_AW* skid buffer
	wire			skids_awvalid, skids_awready;
	wire	[IW-1:0]	skids_awid;
	wire	[AW-1:0]	skids_awaddr;
	wire	[7:0]		skids_awlen;
	wire	[2:0]		skids_awsize;
	wire	[1:0]		skids_awburst;
	//
	// S_AXI_W* skid buffer
	wire			skids_wvalid, skids_wready, skids_wlast;
	wire	[DW-1:0]	skids_wdata;
	wire	[DW/8-1:0]	skids_wstrb;
	//
	// S_AXI_B* skid buffer isn't needed
	//
	// M_AXI_AW* skid buffer isn't needed
	//
	// M_AXI_W* skid buffer
	wire			skidm_wvalid, skidm_wready;
	wire	[DW-1:0]	skidm_wdata;
	wire	[DW/8-1:0]	skidm_wstrb;
	//
	// M_AXI_B* skid buffer
	wire			skidm_bvalid, skidm_bready;
	wire	[1:0]		skidm_bresp;
	//

	generate if (OPT_WRITES)
	begin
		//
		// The write address channel's skid buffer
		skidbuffer #(.DW(IW+AW+8+3+2), .OPT_LOWPOWER(0), .OPT_OUTREG(0))
		awskid(S_AXI_ACLK, !S_AXI_ARESETN,
			S_AXI_AWVALID, S_AXI_AWREADY,
			{ S_AXI_AWID, S_AXI_AWADDR, S_AXI_AWLEN, S_AXI_AWSIZE,
				S_AXI_AWBURST },
			skids_awvalid, skids_awready,
			{ skids_awid, skids_awaddr, skids_awlen, skids_awsize,
				skids_awburst });
		//
		// The write data channel's skid buffer (S_AXI_W*)
		skidbuffer #(.DW(DW+DW/8+1), .OPT_LOWPOWER(0), .OPT_OUTREG(0))
		wskid(S_AXI_ACLK, !S_AXI_ARESETN,
			S_AXI_WVALID, S_AXI_WREADY,
			{ S_AXI_WDATA, S_AXI_WSTRB, S_AXI_WLAST },
			skids_wvalid, skids_wready,
			{ skids_wdata, skids_wstrb, skids_wlast });
		//
		// The downstream AXI-lite write data (M_AXI_W*) skid buffer
		skidbuffer #(.DW(DW+DW/8), .OPT_LOWPOWER(0), .OPT_OUTREG(1))
		mwskid(S_AXI_ACLK, !S_AXI_ARESETN,
			skidm_wvalid, skidm_wready, { skidm_wdata, skidm_wstrb },
			M_AXI_WVALID, M_AXI_WREADY, { M_AXI_WDATA, M_AXI_WSTRB });
		//
		// The downstream AXI-lite response (M_AXI_B*) skid buffer
		skidbuffer #(.DW(2), .OPT_LOWPOWER(0), .OPT_OUTREG(0))
		bskid(S_AXI_ACLK, !S_AXI_ARESETN,
			M_AXI_BVALID, M_AXI_BREADY, { M_AXI_BRESP },
			skidm_bvalid, skidm_bready, { skidm_bresp });

		initial	m_axi_awvalid = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			m_axi_awvalid <= 0;
		else if (skids_awvalid & skids_awready)
			m_axi_awvalid <= 1;
		else if (M_AXI_AWREADY && axi_awlen == 0)
			m_axi_awvalid <= 0;

		assign	M_AXI_AWVALID = m_axi_awvalid;
		assign	skids_awready = (!M_AXI_AWVALID
				|| ((axi_awlen == 0)&&M_AXI_AWREADY))
				&& !wfifo_full
				&&(!s_axi_wready || (skids_wvalid && skids_wlast && skids_wready));

		always @(posedge S_AXI_ACLK)
		if (skids_awvalid && skids_awready)
		begin
			axi_awaddr <= skids_awaddr;
			axi_blen   <= skids_awlen;
			axi_awburst<= skids_awburst;
			axi_awsize <= skids_awsize;
		end else if (M_AXI_AWVALID && M_AXI_AWREADY)
			axi_awaddr <= next_write_addr;

		initial	axi_awlen = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			axi_awlen <= 0;
		else if (skids_awvalid && skids_awready)
			axi_awlen <= skids_awlen;
		else if (M_AXI_AWVALID && M_AXI_AWREADY && axi_awlen > 0)
			axi_awlen <= axi_awlen - 1;

		axi_addr #(.AW(C_AXI_ADDR_WIDTH))
		calcwraddr(axi_awaddr, axi_awsize, axi_awburst,
			axi_blen, next_write_addr);

		// We really don't need to do anything special to the write channel.
		initial	s_axi_wready = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			s_axi_wready <= 0;
		else if (skids_awvalid && skids_awready)
			s_axi_wready <= 1;
		else if (skids_wvalid && skids_wready && skids_wlast)
			s_axi_wready <= 0;


		assign	skidm_wdata  = skids_wdata;
		assign	skidm_wstrb  = skids_wstrb;
		assign	skidm_wvalid = skids_wvalid && s_axi_wready;
		assign	skids_wready = s_axi_wready && skidm_wready;

		assign	read_from_wrfifo = (bcounts <= 1)&&(!wfifo_empty)
			    &&(skidm_bvalid && skidm_bready);

		// BFIFO
		sfifo	#(.BW(C_AXI_ID_WIDTH+8), .LGFLEN(LGFIFO))
			bidlnfifo(S_AXI_ACLK, !S_AXI_ARESETN,
				skids_awvalid && skids_awready,
				{ skids_awid, skids_awlen },
				wfifo_full, wfifo_count,
				read_from_wrfifo,
				{ wfifo_bid, wfifo_bcount }, wfifo_empty);

		// Return counts
		initial	bcounts = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			bcounts <= 0;
		else if (read_from_wrfifo)
		begin
			bcounts <= wfifo_bcount + bcounts;
		end else if (skidm_bvalid && skidm_bready)
			bcounts <= bcounts - 1;

		always @(posedge S_AXI_ACLK)
		if (read_from_wrfifo)
			bid <= wfifo_bid;

		always @(posedge S_AXI_ACLK)
		if (!S_AXI_BVALID || S_AXI_BREADY)
			axi_bid <= (read_from_wrfifo && bcounts==0) ? wfifo_bid : bid;

		initial	s_axi_bvalid = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			s_axi_bvalid <= 0;
		else if (skidm_bvalid && skidm_bready)
			s_axi_bvalid <= (bcounts == 1)
				||((bcounts == 0) && (!wfifo_empty) && (wfifo_bcount == 0));
		else if (S_AXI_BREADY)
			s_axi_bvalid <= 0;

		initial	axi_bresp = 0;
		always @(posedge S_AXI_ACLK)
		if (!S_AXI_ARESETN)
			axi_bresp <= 0;
		else if (S_AXI_BVALID && S_AXI_BREADY)
		begin
			if (skidm_bvalid && skidm_bready)
				axi_bresp <= skidm_bresp;
			else
				axi_bresp <= 0;
		end else if (skidm_bvalid && skidm_bready)
		begin
			// Let SLVERR take priority over DECERR
			casez({ S_AXI_BRESP, skidm_bresp })
			4'b??0?: axi_bresp <= S_AXI_BRESP;
			4'b0?1?: axi_bresp <= skidm_bresp;
			4'b1?10: axi_bresp <= SLVERR;
			4'b1011: axi_bresp <= SLVERR;
			4'b1111: axi_bresp <= skidm_bresp;
			endcase
		end

		assign	M_AXI_AWVALID= m_axi_awvalid;
		assign	M_AXI_AWADDR = axi_awaddr;
		assign	M_AXI_AWPROT = 0;


		assign	skidm_bready = ((bcounts > 0)||(!wfifo_empty))&&(!S_AXI_BVALID | S_AXI_BREADY);
		assign	S_AXI_BID    = axi_bid;
		assign	S_AXI_BRESP  = axi_bresp;
		assign	S_AXI_BVALID = s_axi_bvalid;
	
	end else begin // if (!OPT_WRITES)

		assign	S_AXI_AWREADY = 0;
		assign	S_AXI_WREADY  = 0;
		assign	S_AXI_BID     = 0;
		assign	S_AXI_BRESP   = 2'b11;
		assign	S_AXI_BVALID  = 0;
		assign	S_AXI_BID     = 0;

		//
		assign	M_AXI_AWVALID = 0;
		assign	M_AXI_AWADDR  = 0;
		assign	M_AXI_AWPROT  = 0;
		//
		assign	M_AXI_WVALID  = 0;
		assign	M_AXI_WDATA   = 0;
		assign	M_AXI_WSTRB   = 0;
		//
		assign	M_AXI_BREADY  = 0;

		//
		// S_AXI_AW* skid buffer
		assign	skids_awvalid = 0;
		assign	skids_awready = 0;
		assign	skids_awid    = 0;
		assign	skids_awaddr  = 0;
		assign	skids_awlen   = 0;
		assign	skids_awsize  = 0;
		assign	skids_awburst = 0;
		//
		// S_AXI_W* skid buffer
		assign	skids_wvalid = S_AXI_WVALID;
		assign	skids_wready = S_AXI_WREADY;
		assign	skids_wdata  = S_AXI_WDATA;
		assign	skids_wstrb  = S_AXI_WSTRB;
		assign	skids_wlast  = S_AXI_WLAST;
		//
		// S_AXI_B* skid buffer isn't needed
		//
		// M_AXI_AW* skid buffer isn't needed
		//
		// M_AXI_W* skid buffer
		assign	skidm_wvalid = M_AXI_WVALID;
		assign	skidm_wready = M_AXI_WREADY;
		assign	skidm_wdata  = M_AXI_WDATA;
		assign	skidm_wstrb  = M_AXI_WSTRB;
		//
		// M_AXI_B* skid buffer
		assign	skidm_bvalid = M_AXI_BVALID;
		assign	skidm_bready = M_AXI_BREADY;
		assign	skidm_bresp  = M_AXI_BRESP;
		//
		//
		always @(*)
		begin
			s_axi_wready = 0;

			axi_awlen = 0;
			bcounts  = 0;
			bid      = 0;
			axi_bresp = 0;
			axi_bid   = 0;

		end

		assign	wfifo_full  = 0;
		assign	wfifo_empty = 1;
		assign	wfifo_count = 0;
		assign	read_from_wrfifo = 0;

	end endgenerate

	// Verilator lint_off UNUSED
	wire	[35-1:0]	unused;
	assign	unused = {
		S_AXI_AWLOCK, S_AXI_AWCACHE, S_AXI_AWPROT, S_AXI_AWQOS,
		skids_wlast, wfifo_count};
	// Verilator lint_on  UNUSED

endmodule
`ifndef	YOSYS
`default_nettype wire
`endif
