#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

// Định nghĩa tên trạng thái để chuyển từ số sang chuỗi
char *state_names[] = {
  [0] "UNUSED",
  [1] "SLEEPING",
  [2] "RUNNABLE",
  [3] "RUNNING",
  [4] "ZOMBIE"
};

// Khai báo bộ đệm sự kiện (nên để static để tránh tràn stack)
#define MAX_TRACE_EVENTS 1000
static struct trace_event buf[MAX_TRACE_EVENTS];

int main(void) {
  // Gọi syscall gettrace để lấy dữ liệu từ kernel
  int n = gettrace(buf, MAX_TRACE_EVENTS);
  
  if(n < 0){
    fprintf(2, "dump_logs: syscall failed\n");
    exit(1);
  }

  // BƯỚC QUAN TRỌNG: In Header CSV
  // Dòng này giúp Python xác định được tên các cột
  printf("tick,pid,old_state,new_state\n");

  for(int i = 0; i < n; i++){
    int o  = buf[i].old_state;
    int nw = buf[i].new_state;

    // Giới hạn giá trị để tránh truy cập ngoài mảng state_names
    if(o < 0 || o > 4) o = 0;
    if(nw < 0 || nw > 4) nw = 0;

    // In theo đúng format CSV: tick,pid,old,new
    printf("%d,%d,%s,%s\n",
      buf[i].ticks,
      buf[i].pid,
      state_names[o],
      state_names[nw]);
  }

  exit(0);
}
