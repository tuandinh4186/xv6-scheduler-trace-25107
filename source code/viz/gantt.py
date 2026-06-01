import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from parse_trace import parse_trace, compute_stats

STATE_COLORS = {
    'RUNNING':  '#1D9E75',
    'SLEEPING': '#EF9F27',
    'RUNNABLE': '#AFA9EC',
    'ZOMBIE':   '#E24B4A',
}

def draw_gantt(filepath, title=None, output=None):
    intervals = parse_trace(filepath)
    stats     = compute_stats(intervals)

    if not intervals:
        print("Không có dữ liệu — kiểm tra lại CSV")
        return

    pids    = sorted(set(iv['pid'] for iv in intervals))
    pid_idx = {pid: i for i, pid in enumerate(pids)}
    n_pids  = len(pids)

    if output is None:
        output = filepath.replace('.csv', '_gantt.png')
    if title is None:
        title  = f'Xv6 Scheduler Trace — {filepath}'

    fig_h = max(5, n_pids * 0.7 + 3.5)
    fig   = plt.figure(figsize=(15, fig_h), facecolor='white')
    ax_g  = fig.add_axes([0.08, 0.28, 0.88, 0.64])
    ax_s  = fig.add_axes([0.08, 0.02, 0.88, 0.20])

    # ── Vẽ thanh Gantt ──
    t_min = min(iv['start'] for iv in intervals)
    t_max = max(iv['end']   for iv in intervals)
    span  = max(t_max - t_min, 1)

    for iv in intervals:
        y   = pid_idx[iv['pid']]
        dur = iv['end'] - iv['start']
        if dur <= 0:
            continue
        color = STATE_COLORS.get(iv['state'], '#888888')
        ax_g.broken_barh(
            [(iv['start'], dur)],
            (y - 0.38, 0.76),
            facecolors=color,
            edgecolors='white',
            linewidth=0.5,
            alpha=0.88
        )
        # In PID lên thanh nếu đủ rộng
        if dur > span * 0.03:
            ax_g.text(
                iv['start'] + dur / 2, y,
                str(iv['pid']),
                ha='center', va='center',
                fontsize=8, color='white', fontweight='bold'
            )

    ax_g.set_yticks(range(n_pids))
    ax_g.set_yticklabels([f'PID {p}' for p in pids], fontsize=10)
    ax_g.set_xlabel('CPU Ticks', fontsize=11)
    ax_g.set_title(title, fontsize=13, pad=12, fontweight='bold')
    ax_g.grid(axis='x', linestyle='--', alpha=0.3, linewidth=0.5)
    ax_g.set_axisbelow(True)
    ax_g.invert_yaxis()

    # Legend — chỉ hiện state có trong data
    handles = [
        mpatches.Patch(color=c, label=s)
        for s, c in STATE_COLORS.items()
        if any(iv['state'] == s for iv in intervals)
    ]
    ax_g.legend(
        handles=handles,
        loc='upper right',
        fontsize=9,
        framealpha=0.88,
        ncol=len(handles),
        title='Process State'
    )

    # ── Stats table ──
    ax_s.axis('off')
    col_labels = ['Total Ticks', 'CPU Util (%)', 'Avg Turnaround',
                  'Avg Waiting', 'Processes']
    col_keys   = ['total_ticks', 'cpu_utilization', 'avg_turnaround',
                  'avg_waiting', 'n_processes']
    values = [[str(stats.get(k, 'N/A')) for k in col_keys]]

    tbl = ax_s.table(
        cellText=values,
        colLabels=col_labels,
        loc='center',
        cellLoc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 2.0)

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor('#EEEDFE')
            cell.set_text_props(fontweight='bold', color='#534AB7')
            cell.set_edgecolor('#AFA9EC')
        else:
            cell.set_facecolor('#F8F8FC')
            cell.set_edgecolor('#D0D0E8')

    plt.savefig(output, dpi=150, bbox_inches='tight')
    print(f"Saved: {output}")
    plt.close()


if __name__ == '__main__':
    fp  = sys.argv[1] if len(sys.argv) > 1 else 'trace_cpu.csv'
    ttl = sys.argv[2] if len(sys.argv) > 2 else None
    draw_gantt(fp, title=ttl)
