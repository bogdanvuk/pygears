#include "svdpi.h"
#include <stdio.h>

#define MAX_ARR_SIZE 8

struct array_handle {
	uint32_t data[MAX_ARR_SIZE];
	int size;
};


int svSize(const svOpenArrayHandle h, int d) {
	struct array_handle* arr = h;
	return arr->size;
}

void *svGetArrayPtr(const svOpenArrayHandle h) {
	struct array_handle* arr = h;
	return arr->data;
}

int sock_done(void* handle);
int sock_get(void* handle, svOpenArrayHandle signal);
void* sock_open(const char* uri, const char* channel);
void sock_close(void* handle);
int sock_put(void* handle, const svOpenArrayHandle signal);

int main() {
	void* in_handle;
	void* out_handle;
	in_handle = sock_open("tcp://localhost:1234", "din");
	out_handle = sock_open("tcp://localhost:1234", "dout");

	printf("Socket opened\n");

	struct array_handle signal;
	signal.size = 1;

	while(sock_get(in_handle, (svOpenArrayHandle) &signal) == 0) {
		printf("Received %x\n", signal.data[0]);
		sock_done(in_handle);
		sock_put(out_handle, (svOpenArrayHandle) &signal);
	}

/* 	svBitVecVal signal[1]; */
/* 	while (sock_get(handle, signal) == 0) { */
/* 		printf("Received: 0x%x\n", signal[0]); */
/* 	} */

	sock_close(in_handle);
	sock_close(out_handle);

	return 0;

}
