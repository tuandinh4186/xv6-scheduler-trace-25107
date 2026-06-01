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

def draw_one(ax, intervals, title):
    pids    = sorted(set(iv['pid'] for iv in intervals))
    pid_idx = {pid: i for i, pid in enumerate(pids)}
    t_min   = min(iv['start'] for iv in intervals)
    t_max   = max(iv['end']   for iv in intervals)
    span    = max(t_max - t_min, 1)

    for iv in intervals:
        y   = pid_idx[iv['pid']]
        dur = iv['end'] - iv['start']
        if dur <= 0: continue
        ax.broken_barh(
            [(iv['start'], dur)], (y - 0.38, 0.76),
            facecolors=STATE_COLORS.get(iv['state'], '#888'),
            edgecolors='white', linewidth=0.4, alpha=0.88
        )
        if dur > span * 0.04:
            ax.text(iv['start'] + dur/2, y, str(iv['pid']),
                    ha='center', va='center',
                    fontsize=8, color='white', fontweight='bold')

    ax.set_yticks(range(len(pids)))
    ax.set_yticklabels([f'PID {p}' for p in pids], fontsize=9)
    ax.set_xlabel('CPU Ticks', fontsize=10)
    ax.set_title(title, fontsize=11, pad=8, fontweight='bold')
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.invert_yaxis()


def compare(file_cpu, file_io, output='comparison.png'):
    iv_cpu = parse_trace(file_cpu)
    iv_io  = parse_trace(file_io)
    s_cpu  = compute_stats(iv_cpu)
    s_io   = compute_stats(iv_io)

    fig, axes = plt.subplots(1, 2, figsize=(18, 7), facecolor='white')
    draw_one(axes[0], iv_cpu, 'CPU-bound Workload')
    draw_one(axes[1], iv_io,  'I/O-bound Workload')

    # Legend chung
    handles = [mpatches.Patch(color=c, label=s)
               for s, c in STATE_COLORS.items()]
    fig.legend(handles=handles, loc='upper center', ncol=4,
               fontsize=9, framealpha=0.88,
               bbox_to_anchor=(0.5, 1.01), title='Process State')

    # Bảng so sánh
    fig.subplots_adjust(bottom=0.25, top=0.90)
    ax_t = fig.add_axes([0.05, 0.01, 0.90, 0.18])
    ax_t.axis('off')

    metrics = ['cpu_utilization', 'avg_turnaround', 'avg_waiting', 'n_processes']
    mlabels = ['CPU Util (%)', 'Avg Turnaround', 'Avg Waiting', 'Processes']
    table_data = [
        ['CPU-bound'] + [str(s_cpu.get(k, 'N/A')) for k in metrics],
        ['I/O-bound']  + [str(s_io.get(k, 'N/A'))  for k in metrics],
    ]
    tbl = ax_t.table(
        cellText=table_data,
        colLabels=['Workload'] + mlabels,
        loc='center', cellLoc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 2.2)

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor('#EEEDFE')
            cell.set_text_props(fontweight='bold', color='#534AB7')
        elif r == 1:
            cell.set_facecolor('#E8FAF4')
        else:
            cell.set_facecolor('#FDF2EE')
        cell.set_edgecolor('#D0D0D8')

    plt.savefig(output, dpi=150, bbox_inches='tight')
    print(f"Saved: {output}")
    plt.close()

    # In bảng ra terminal — copy vào báo cáo chương 6
    print("\n" + "="*55)
    print(f"{'Metric':<22} {'CPU-bound':>15} {'I/O-bound':>15}")
    print("-"*55)
    for k, lbl in zip(metrics, mlabels):
        print(f"{lbl:<22} {str(s_cpu.get(k,'N/A')):>15} {str(s_io.get(k,'N/A')):>15}")
    print("="*55)


if __name__ == '__main__':
    import sys
    fc = sys.argv[1] if len(sys.argv) > 1 else 'trace_cpu.csv'
    fi = sys.argv[2] if len(sys.argv) > 2 else 'trace_io.csv'
    compare(fc, fi)
