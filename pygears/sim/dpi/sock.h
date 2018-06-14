#ifndef PYGEARS_SOCK_H
#define PYGEARS_SOCK_H

#include "svdpi.h"

int sock_done(void* handle);
int sock_get(void* handle, svOpenArrayHandle signal);
void* sock_open(const char* uri, const char* channel);
void sock_close(void* handle);
int sock_put(void* handle, const svOpenArrayHandle signal);

#endif
