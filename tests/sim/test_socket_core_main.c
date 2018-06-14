#include "svdpi.h"
#include <stdio.h>
#include <stdlib.h>

#define MAX_ARR_SIZE 128

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

int main(int argc, char *argv[]) {
	void* in_handle;
	void* out_handle;
	in_handle = sock_open("tcp://localhost:1234", "din");
	out_handle = sock_open("tcp://localhost:1234", "dout");

	printf("Socket opened\n");

	struct array_handle signal;
	signal.size = atoi(argv[1]);
	printf("Signal of size %d", signal.size);

	while(sock_get(in_handle, (svOpenArrayHandle) &signal) == 0) {
		printf("Received %x\n", signal.data[0]);
		sock_done(in_handle);
		sock_put(out_handle, (svOpenArrayHandle) &signal);
	}

	sock_close(in_handle);
	sock_close(out_handle);

	return 0;

}
