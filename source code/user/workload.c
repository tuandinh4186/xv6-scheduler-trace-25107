#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int main(void) {
  printf("Starting heavy workload...\n");
  for(int i = 0; i < 5; i++){
    int pid = fork();
    if(pid == 0){
      // Tăng số vòng lặp lên để tiến trình chạy lâu hơn
      // 100,000,000 vòng lặp sẽ giúp vạch xanh dài ra đáng kể
      volatile int x = 0;
      for(int j = 0; j < 100000000; j++) {
          x += j;
      }
      exit(0);
    }
  }
  
  // Chờ tất cả 5 tiến trình con kết thúc
  for(int i = 0; i < 5; i++) wait(0);
  
  printf("workload done\n");
  exit(0);
}
