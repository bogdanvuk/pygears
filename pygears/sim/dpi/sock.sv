package sock;

// Tested on modelsim altera starter edition for linux
//
// Example compile command:
//    vlog example.sv sock.sv sock.c
//
// Example run command (windows):
//    vsim example -ldflags -lws2_32
//
// Example run command (linux):
//    vsim example

// Open a connection to an endpoint
//   uri - Where to connect:
//           tcp://hostname:port - TCP Socket.
//           unix://socketname   - Unix Domain Socket (linux only).
//                                 Prefix with @ for abstract namespace.
//   channel - The name of the pygears channel to connect to
//
// Returns a handle to be used with other functions, or null on error
import "DPI-C" function chandle sock_open(input string uri, input string channel);

// Close a connection to an endpoint
//   handle - Handle returned from sock_open
import "DPI-C" function void sock_close(input chandle handle);

// Returns 1 on success, 0 on error
import "DPI-C" function int sock_get(input chandle handle, output logic [] signal, input int width);


// Returns 1 on success, 0 on error
import "DPI-C" function int sock_put(input chandle handle, input logic [] signal, input int width);

endpackage
