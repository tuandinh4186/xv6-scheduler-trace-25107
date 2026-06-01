#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"
#include "kernel/fcntl.h"

int main(void) {
  int n = 4; // 4 tiến trình I/O-bound

  for(int i = 0; i < n; i++){
    int pid = fork();
    if(pid == 0){
      // Tên file riêng mỗi child: tmp0, tmp1, tmp2, tmp3
      char fname[5];
      fname[0]='t'; fname[1]='m'; fname[2]='p';
      fname[3]='0'+i; fname[4]='\0';

      // Lặp: tạo file → ghi → đọc lại → xóa
      // Mỗi vòng: 2 syscall I/O → bị block → SLEEPING
      for(int r = 0; r < 20; r++){
        int fd = open(fname, O_CREATE|O_WRONLY);
        if(fd >= 0){
          write(fd, "scheduler_trace\n", 16);
          close(fd);
        }
        fd = open(fname, O_RDONLY);
        if(fd >= 0){
          char buf[32];
          read(fd, buf, 16);
          close(fd);
        }
      }
      unlink(fname);
      exit(0);
    }
  }

  // Parent chờ tất cả con xong
  for(int i = 0; i < n; i++) wait(0);
  printf("io workload done\n");
  exit(0);
}
