#include "svdpi.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifdef _WIN32
// Need to say we are on recent enough windows to get getaddrinfo...
// http://stackoverflow.com/questions/12765743/getaddrinfo-on-win32
#define _WIN32_WINNT 0x0501
#include <winsock2.h>
#include <ws2tcpip.h>
#endif /* _WIN32 */

#if defined __linux__
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <netinet/tcp.h>
#include <sys/types.h>
#include <sys/un.h>

typedef int SOCKET;
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket(s) close(s);
#endif /* __linux__ */

// Thanks: http://beej.us/guide/bgnet/
//         https://github.com/jimloco/Csocket

#define BUFFER_SIZE (1024 / 32 * sizeof(uint32_t))
struct handle {
  SOCKET sock;
  char wbuf[BUFFER_SIZE];
  char rbuf[BUFFER_SIZE + 1];
  size_t roff; // Read pointer
  size_t eoff; // Read end
  int timeout;
};

int sock_init() {
#ifdef _WIN32
  // Init the windows sockets
  WSADATA wsaData;
  if (WSAStartup(MAKEWORD(2, 2), &wsaData) != NO_ERROR) {
    return -1;
  }
#endif /* _WIN32 */
  return 0;
}

void sock_shutdown() {
#ifdef _WIN32
  WSACleanup();
#endif /* _WIN32 */
}

struct handle *init_struct(SOCKET sock, int timeout) {
  struct handle *h = malloc(sizeof(struct handle));
  if (h) {
    h->sock = sock;
    h->roff = 0;
    h->eoff = 0;
    h->rbuf[BUFFER_SIZE] = '\0'; // Overflow protection for long strings
    h->timeout = timeout;
  }
  return h;
}

void *tcp_sock_open(const char *name, int timeout) {
  // Extract hostname / port
  char *string = strdup(name);
  if (!string)
    return NULL;
  char *colon = strchr(string, ':');
  if (!colon) {
    free(string);
    return NULL;
  }
  *colon = '\0'; // Split string into hostname and port
  const char *hostname = string;
  const char *port = colon + 1;

  int status;
  struct addrinfo hints, *res, *p;

  // Setup hints - we want TCP and dont care if its IPv6 or IPv4
  memset(&hints, 0, sizeof hints);
  hints.ai_family = AF_UNSPEC; // AF_INET or AF_INET6 to force version
  hints.ai_socktype = SOCK_STREAM;

  // Look up the host
  if ((status = getaddrinfo(hostname, port, &hints, &res)) != 0) {
    free(string);
    return NULL;
  }
  free(string);

  // Try and connect
  SOCKET sock = INVALID_SOCKET;
  for (p = res; sock == INVALID_SOCKET && p != NULL; p = p->ai_next) {
    sock = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
    if (sock != INVALID_SOCKET) {
      status = connect(sock, p->ai_addr, p->ai_addrlen);
      if (status == SOCKET_ERROR) {
        closesocket(sock);
        sock = INVALID_SOCKET;
      }
    }
  }
  freeaddrinfo(res); // free the linked list
  if (sock == INVALID_SOCKET) {
    return NULL;
  }

  // Timeout
  if (timeout > 0) {
    struct timeval tim_str;
    tim_str.tv_sec = timeout;
    tim_str.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char *)&tim_str,
               sizeof(tim_str));

    int one = 1;
    setsockopt(sock, SOL_TCP, TCP_NODELAY, &one, sizeof(one));
  } else if (timeout == 0) {
    if (fcntl(sock, F_SETFL, fcntl(sock, F_GETFL) | O_NONBLOCK) < 0) {
      // printf("Error while putting the socket in non-blocking mode\n");
    }
  }

  // Create handle
  return init_struct(sock, timeout);
}

#ifdef __linux__
void *unix_sock_open(const char *name) {
  // Build endpoint details
  struct sockaddr_un endpoint;
  if (strlen(name) == 0 || strlen(name) > sizeof(endpoint.sun_path))
    return NULL; // Invalid socket name
  endpoint.sun_family = AF_UNIX;
  strcpy(endpoint.sun_path, name);
  size_t len = strlen(endpoint.sun_path) + sizeof(endpoint.sun_family);
  if (endpoint.sun_path[0] == '@')
    endpoint.sun_path[0] = '\0'; // Use @ for abstract namespace

  // Create socket
  SOCKET sock = socket(AF_UNIX, SOCK_STREAM, 0);
  if (sock == INVALID_SOCKET) {
    return NULL;
  }

  // Connect
  if (connect(sock, (struct sockaddr *)&endpoint, len) == SOCKET_ERROR) {
    closesocket(sock);
    return NULL;
  }

  // Create handle
  return init_struct(sock, 0);
}
#endif

void *sock_open(const char *uri, const char *channel) {
  /* printf("[sock_open] enter\n"); */
  size_t len = strlen(uri);
  struct handle *handle = NULL;

  // printf("Waiting on socket connection...\n");
  do {
    if (len > 6 && strncmp("tcp://", uri, 6) == 0) {
      if (strncmp(channel, "_synchro", 10) == 0)
        handle = tcp_sock_open(uri + 6, 2);
      else
        handle = tcp_sock_open(uri + 6, 0);
    }
#ifdef __linux__
    else if (len > 7 && strncmp("unix://", uri, 7) == 0) {
      handle = unix_sock_open(uri + 7);
    }
#endif
    if (handle == NULL) {
      usleep(200000);
    }
  } while (handle == NULL);

  send(handle->sock, channel, strlen(channel), 0);
  // printf("Opened socket for %s: %p, timeout=%d\n", channel, handle,
  /* handle->timeout); */

  /* printf("[sock_open] exit\n"); */
  return handle;
}

void sock_close(void *handle) {
  if (!handle)
    return;

  struct handle *h = handle;
  closesocket(h->sock);
  free(h);
}

int sock_done(void *handle) {
  // Validate input
  if (!handle)
    return 0; // Invalid handle

  struct handle *h = handle;

  int ret;
  uint32_t val = 0;
  ret = send(h->sock, &val, 4, 0);
  if (ret < 0) {
    return 1;
  } else {
    return 0;
  }
}

/* int print_time() { */
/*   FILE *fp; */
/*   char path[1035]; */

/*   /\* Open the command for reading. *\/ */
/*   fp = popen("date +%s.%N", "r"); */
/*   if (fp == NULL) { */
/*     printf("Failed to run command\n" ); */
/*     exit(1); */
/*   } */

/*   /\* Read the output a line at a time - output it. *\/ */
/*   while (fgets(path, sizeof(path)-1, fp) != NULL) { */
/*     printf("%s", path); */
/*   } */

/*   /\* close *\/ */
/*   pclose(fp); */
/* } */

extern void pause_sim();

int sock_get_bv(void *handle, int width, svBitVecVal *signal) {
  // Validate input
  if (!handle) {
    return 1;
  }

  struct handle *h = handle;
  int ret;
  int words = SV_PACKED_DATA_NELEMS(width);

  do {
    /* ret = recv(h->sock, h->rbuf, BUFFER_SIZE, 0); */
    /* ret = recv(h->sock, h->rbuf, words * 4, 0); */
    ret = recv(h->sock, signal, words * 4, 0);

    /* printf("Got: "); */
    /* print_time(); */

    /* printf("Ret value %d for width %d, errno value %d\n", ret, words*4, errno); */
    if (ret <= 0) {
      if ((errno == EAGAIN) || (errno == EWOULDBLOCK)) {
        if (h->timeout > 0) {
          /* printf("%p timeout\n", handle); */
          /* printf("Ret value %d, errno value %d\n", ret, errno); */
          pause_sim();
        } else if (h->timeout == 0) {
          return 2;
        }
      } else if (errno != EINTR) {
        /* printf("Ret value %d, errno value %d\n", ret, errno); */
        return 1;
      }
    }
  } while (ret <= 0);

  /* uint32_t *rval = (uint32_t *)h->rbuf; */

  /* int i; */
  /* for (i = 0; i < SV_PACKED_DATA_NELEMS(width); i++) { */
  /*   printf("%x ", signal[i]); */
  /*   /\* printf("%x ", rval[i]); *\/ */
  /*   /\* signal[i] = rval[i]; *\/ */
  /* } */

  /* printf("\n"); */

  return 0;
}

int sock_get(void *handle, const svOpenArrayHandle signal) {
  /* printf("[sock_get] enter\n"); */
  int ret = sock_get_bv(handle, svSize(signal, 0), (svBitVecVal *) svGetArrayPtr(signal));
  /* printf("[sock_get] exit with %d\n", ret); */
  return ret;
}


int sock_put(void *handle, const svOpenArrayHandle signal) {
  // Validate input
  if (!handle) {
    return 1;
  }

  /* printf("Put: "); */
  /* print_time(); */
  struct handle *h = handle;
  int width = svSize(signal, 0);
  const svBitVecVal *ptr = (const svBitVecVal *)svGetArrayPtr(signal);

  /* printf("Width: %d\n", width); */
  /* printf("Sending %d bytes\n", SV_PACKED_DATA_NELEMS(width) * sizeof(svBitVecVal)); */

  send(h->sock, ptr, SV_PACKED_DATA_NELEMS(width) * sizeof(svBitVecVal), 0);

  return 0;
}

/* int main() { */
/* 	struct handle* handle; */

/* 	handle = sock_open("tcp://localhost:1234", "cfg"); */

/* 	// printf("Socket opened\n"); */

/* 	svBitVecVal signal[1]; */
/* 	while (sock_get(handle, signal) == 0) { */
/* 		// printf("Received: 0x%x\n", signal[0]); */
/* 	} */

/* 	sock_close(handle); */

/* 	return 0; */

/* } */
