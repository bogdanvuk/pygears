Relevant blog: http://www.anthonyvh.com/2017/10/13/questasim_on_ubuntu/

Error:

In file included from /tools/home/pygears/pygears/sim/dpi/sock.c:1:0:
/usr/include/stdio.h:27:36: fatal error: bits/libc-header-start.h: No such file or directory
 #include <bits/libc-header-start.h>

Fix:

sudo apt-get install gcc-multilib g++-multilib



Error:

ld: /usr/lib/x86_64-linux-gnu/crti.o: unrecognized relocation (0x2a) in section `.init'
ld: final link failed: Bad value

Fix:

cd <ncsim_install_dir>/tools/cdsgcc/gcc/4.8/bin/
cp ld ld_bkp
ln -s /usr/bin/ld ld
