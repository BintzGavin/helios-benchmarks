#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
__attribute__((constructor)) static void trace(void){const char *p=getenv("BRIDGE_CPU_PROFILE_LOG");if(!p)return;int fd=open(p,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd>=0){write(fd,"CPU_PROFILE_CONSTRUCTOR_NO_GPU\n",31);close(fd);}}
