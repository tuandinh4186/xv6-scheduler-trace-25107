import csv
from collections import defaultdict

def parse_trace(filepath):
    events = []
    with open(filepath, 'r') as f:
        for row in csv.DictReader(f):
            tick_str = row.get('tick', '').strip()
            if not tick_str or tick_str.startswith('#'):
                continue
            try:
                pid = int(row['pid'])
                if pid <= 2:  # bỏ init và sh
                    continue
                tick = int(tick_str)
                if tick < 10:  # bỏ boot events
                    continue
                events.append({
                    'tick':      tick,
                    'pid':       pid,
                    'old_state': row['old_state'].strip(),
                    'new_state': row['new_state'].strip(),
                })
            except (ValueError, KeyError):
                continue

    events.sort(key=lambda e: (e['tick'], e['pid']))

    # Fix tick trùng: gán tăng dần để tính được duration
    for i in range(1, len(events)):
        if events[i]['tick'] <= events[i-1]['tick']:
            events[i]['tick'] = events[i-1]['tick'] + 1

    last      = {}
    intervals = []
    for ev in events:
        pid, tick = ev['pid'], ev['tick']
        if pid in last:
            prev = last[pid]
            dur  = tick - prev['start']
            if dur > 0 and prev['state'] in ('RUNNING','SLEEPING','RUNNABLE'):
                intervals.append({
                    'pid':   pid,
                    'state': prev['state'],
                    'start': prev['start'],
                    'end':   tick,
                })
        last[pid] = {'state': ev['new_state'], 'start': tick}

    return intervals


def compute_stats(intervals):
    if not intervals:
        return {}

    t_start = min(iv['start'] for iv in intervals)
    t_end   = max(iv['end']   for iv in intervals)
    total   = t_end - t_start
    if total == 0:
        return {}

    run_time = sum(iv['end']-iv['start'] for iv in intervals
                   if iv['state'] == 'RUNNING')
    cpu_util = run_time / total * 100

    pid_data = defaultdict(lambda: {
        'first': None, 'last_run_end': 0, 'wait': 0
    })
    for iv in intervals:
        pid = iv['pid']
        dur = iv['end'] - iv['start']
        if pid_data[pid]['first'] is None:
            pid_data[pid]['first'] = iv['start']
        if iv['state'] == 'RUNNABLE':
            pid_data[pid]['wait'] += dur
        if iv['state'] == 'RUNNING':
            pid_data[pid]['last_run_end'] = max(
                pid_data[pid]['last_run_end'], iv['end'])

    turnarounds = [
        d['last_run_end'] - d['first']
        for d in pid_data.values()
        if d['first'] is not None and d['last_run_end']
    ]
    waits = [d['wait'] for d in pid_data.values()]

    return {
        'total_ticks':     total,
        'cpu_utilization': round(cpu_util, 2),
        'avg_turnaround':  round(sum(turnarounds)/len(turnarounds), 2) if turnarounds else 0,
        'avg_waiting':     round(sum(waits)/len(waits), 2) if waits else 0,
        'n_processes':     len(pid_data),
    }


if __name__ == '__main__':
    import sys
    fp  = sys.argv[1] if len(sys.argv) > 1 else 'trace_cpu.csv'
    ivs = parse_trace(fp)
    print(f"\n=== Kết quả phân tích từ: {fp} ===")
    print(f"Số lượng khoảng thời gian: {len(ivs)}")
    for k, v in compute_stats(ivs).items():
        print(f"  {k:<22}: {v}")
