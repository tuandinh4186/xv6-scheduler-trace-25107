#ifndef TRACE_H
#define TRACE_H

#define MAX_TRACE_EVENTS 1000

struct trace_event {
  int  pid;
  int  old_state;
  int  new_state;
  uint ticks;
};

// Tên state theo index của enum procstate trong Xv6
static char *state_names[] = {
  "UNUSED", "SLEEPING", "RUNNABLE", "RUNNING", "ZOMBIE"
};

#endif
