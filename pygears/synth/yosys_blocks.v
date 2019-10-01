module \$alu (A, B, CI, BI, X, Y, CO);

parameter A_SIGNED = 0;
parameter B_SIGNED = 0;
parameter A_WIDTH = 1;
parameter B_WIDTH = 1;
parameter Y_WIDTH = 1;

input [A_WIDTH-1:0] A;
input [B_WIDTH-1:0] B;
output [Y_WIDTH-1:0] X, Y;

input CI, BI;
output [Y_WIDTH-1:0] CO;

wire [Y_WIDTH-1:0] AA, BB;

generate
	if (A_SIGNED && B_SIGNED) begin:BLOCK1
		assign AA = $signed(A), BB = BI ? ~$signed(B) : $signed(B);
	end else begin:BLOCK2
		assign AA = $unsigned(A), BB = BI ? ~$unsigned(B) : $unsigned(B);
	end
endgenerate

// this is 'x' if Y and CO should be all 'x', and '0' otherwise
wire y_co_undef = ^{A, A, B, B, CI, CI, BI, BI};

assign X = AA ^ BB;
assign Y = (AA + BB + CI) ^ {Y_WIDTH{y_co_undef}};

function get_carry;
	input a, b, c;
	get_carry = (a&b) | (a&c) | (b&c);
endfunction

genvar i;
generate
	assign CO[0] = get_carry(AA[0], BB[0], CI) ^ y_co_undef;
	for (i = 1; i < Y_WIDTH; i = i+1) begin:BLOCK3
		assign CO[i] = get_carry(AA[i], BB[i], CO[i-1]) ^ y_co_undef;
	end
endgenerate

endmodule
