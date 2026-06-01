import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QTabWidget, QSplitter,
    QFrame, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from parse_trace import parse_trace, compute_stats

STATE_COLORS = {
    'RUNNING':  '#1D9E75',
    'SLEEPING': '#EF9F27',
    'RUNNABLE': '#AFA9EC',
    'ZOMBIE':   '#E24B4A',
}


class GanttCanvas(FigureCanvas):
    """Widget matplotlib nhúng vào PyQt"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(12, 5), facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)

    def plot(self, intervals, title='Scheduler Trace'):
        self.fig.clear()
        if not intervals:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Không có dữ liệu',
                    ha='center', va='center', fontsize=14,
                    color='#888780')
            self.draw()
            return

        ax    = self.fig.add_subplot(111)
        pids  = sorted(set(iv['pid'] for iv in intervals))
        pidx  = {pid: i for i, pid in enumerate(pids)}
        t_min = min(iv['start'] for iv in intervals)
        t_max = max(iv['end']   for iv in intervals)
        span  = max(t_max - t_min, 1)

        for iv in intervals:
            y   = pidx[iv['pid']]
            dur = iv['end'] - iv['start']
            if dur <= 0: continue
            ax.broken_barh(
                [(iv['start'], dur)], (y - 0.38, 0.76),
                facecolors=STATE_COLORS.get(iv['state'], '#888'),
                edgecolors='white', linewidth=0.5, alpha=0.88
            )
            if dur > span * 0.03:
                ax.text(iv['start'] + dur/2, y,
                        str(iv['pid']),
                        ha='center', va='center',
                        fontsize=8, color='white', fontweight='bold')

        ax.set_yticks(range(len(pids)))
        ax.set_yticklabels([f'PID {p}' for p in pids], fontsize=10)
        ax.set_xlabel('CPU Ticks', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.invert_yaxis()

        handles = [
            mpatches.Patch(color=c, label=s)
            for s, c in STATE_COLORS.items()
            if any(iv['state'] == s for iv in intervals)
        ]
        ax.legend(handles=handles, loc='upper right',
                  fontsize=9, ncol=len(handles))

        self.fig.tight_layout()
        self.draw()


class StatsTable(QTableWidget):
    """Bảng hiển thị metrics"""
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Metric', 'CPU-bound', 'I/O-bound'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        # Style header
        self.setStyleSheet("""
            QHeaderView::section {
                background-color: #EEEDFE;
                color: #534AB7;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #AFA9EC;
            }
            QTableWidget {
                border: 0.5px solid #D0D0D8;
                border-radius: 6px;
            }
        """)

    def update_stats(self, stats_cpu, stats_io):
        metrics = [
            ('CPU Utilization (%)', 'cpu_utilization'),
            ('Avg Turnaround',      'avg_turnaround'),
            ('Avg Waiting',         'avg_waiting'),
            ('Total Ticks',         'total_ticks'),
            ('Processes',           'n_processes'),
        ]
        self.setRowCount(len(metrics))
        for i, (label, key) in enumerate(metrics):
            self.setItem(i, 0, QTableWidgetItem(label))
            v_cpu = str(stats_cpu.get(key, 'N/A'))
            v_io  = str(stats_io.get(key,  'N/A'))
            self.setItem(i, 1, QTableWidgetItem(v_cpu))
            self.setItem(i, 2, QTableWidgetItem(v_io))

            # Tô màu so sánh
            for col, val in [(1, v_cpu), (2, v_io)]:
                item = self.item(i, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Xv6 Scheduler Visualization Tool')
        self.setMinimumSize(1100, 700)
        self.intervals_cpu = []
        self.intervals_io  = []
        self.stats_cpu     = {}
        self.stats_io      = {}
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── Sidebar trái ──
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QFrame {
                background: #F8F8FC;
                border: 0.5px solid #D0D0D8;
                border-radius: 10px;
            }
        """)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(10)

        # Title sidebar
        title = QLabel('Scheduler\nVisualization')
        title.setFont(QFont('sans-serif', 14, QFont.Bold))
        title.setStyleSheet('color: #534AB7; background: transparent; border: none;')
        title.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('background: #D0D0D8; border: none; max-height: 1px;')
        side_layout.addWidget(sep)

        # Buttons
        btn_cpu = self._make_button('📂 Load CPU-bound CSV', '#1D9E75')
        btn_cpu.clicked.connect(lambda: self._load_file('cpu'))
        side_layout.addWidget(btn_cpu)

        btn_io = self._make_button('📂 Load I/O-bound CSV', '#D85A30')
        btn_io.clicked.connect(lambda: self._load_file('io'))
        side_layout.addWidget(btn_io)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet('background: #D0D0D8; border: none; max-height: 1px;')
        side_layout.addWidget(sep2)

        btn_compare = self._make_button('⚖️ So sánh', '#534AB7')
        btn_compare.clicked.connect(self._show_compare)
        side_layout.addWidget(btn_compare)

        btn_export = self._make_button('💾 Export PNG', '#888780')
        btn_export.clicked.connect(self._export_png)
        side_layout.addWidget(btn_export)

        # Status labels
        self.lbl_cpu = QLabel('CPU-bound: chưa load')
        self.lbl_io  = QLabel('I/O-bound: chưa load')
        for lbl in [self.lbl_cpu, self.lbl_io]:
            lbl.setStyleSheet('font-size: 11px; color: #888780; '
                              'background: transparent; border: none;')
            lbl.setWordWrap(True)
            side_layout.addWidget(lbl)

        side_layout.addStretch()

        # Legend
        for state, color in STATE_COLORS.items():
            row = QWidget()
            row.setStyleSheet('background: transparent; border: none;')
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            dot = QLabel('●')
            dot.setStyleSheet(f'color: {color}; font-size: 14px; '
                              f'background: transparent; border: none;')
            lbl = QLabel(state)
            lbl.setStyleSheet('font-size: 11px; color: #444; '
                              'background: transparent; border: none;')
            rl.addWidget(dot)
            rl.addWidget(lbl)
            rl.addStretch()
            side_layout.addWidget(row)

        main_layout.addWidget(sidebar)

        # ── Main content ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 0.5px solid #D0D0D8;
                border-radius: 8px;
            }
            QTabBar::tab {
                padding: 8px 20px;
                font-size: 13px;
                border-radius: 6px 6px 0 0;
            }
            QTabBar::tab:selected {
                background: #EEEDFE;
                color: #534AB7;
                font-weight: bold;
            }
        """)

        # Tab 1: CPU-bound
        tab_cpu = QWidget()
        tl1 = QVBoxLayout(tab_cpu)
        self.canvas_cpu = GanttCanvas()
        self.toolbar_cpu = NavigationToolbar(self.canvas_cpu, self)
        tl1.addWidget(self.toolbar_cpu)
        tl1.addWidget(self.canvas_cpu)
        self.tabs.addTab(tab_cpu, 'CPU-bound')

        # Tab 2: I/O-bound
        tab_io = QWidget()
        tl2 = QVBoxLayout(tab_io)
        self.canvas_io = GanttCanvas()
        self.toolbar_io = NavigationToolbar(self.canvas_io, self)
        tl2.addWidget(self.toolbar_io)
        tl2.addWidget(self.canvas_io)
        self.tabs.addTab(tab_io, 'I/O-bound')

        # Tab 3: So sánh
        tab_cmp = QWidget()
        tl3 = QVBoxLayout(tab_cmp)
        self.canvas_cmp = GanttCanvas()
        tl3.addWidget(self.canvas_cmp)
        self.stats_table = StatsTable()
        self.stats_table.setMaximumHeight(200)
        tl3.addWidget(QLabel('Bảng so sánh metrics:'))
        tl3.addWidget(self.stats_table)
        self.tabs.addTab(tab_cmp, '⚖️ So sánh')

        main_layout.addWidget(self.tabs)

    def _make_button(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        return btn

    def _load_file(self, kind):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn file CSV', os.path.expanduser('~/viz'),
            'CSV files (*.csv)'
        )
        if not path:
            return

        intervals = parse_trace(path)
        stats     = compute_stats(intervals)
        fname     = os.path.basename(path)

        if kind == 'cpu':
            self.intervals_cpu = intervals
            self.stats_cpu     = stats
            self.canvas_cpu.plot(intervals, f'CPU-bound — {fname}')
            self.lbl_cpu.setText(f'CPU-bound: {fname}\n'
                                 f'({len(intervals)} intervals, '
                                 f'{stats.get("n_processes","?")} PIDs)')
            self.tabs.setCurrentIndex(0)
        else:
            self.intervals_io = intervals
            self.stats_io     = stats
            self.canvas_io.plot(intervals, f'I/O-bound — {fname}')
            self.lbl_io.setText(f'I/O-bound: {fname}\n'
                                f'({len(intervals)} intervals, '
                                f'{stats.get("n_processes","?")} PIDs)')
            self.tabs.setCurrentIndex(1)

    def _show_compare(self):
        if not self.intervals_cpu and not self.intervals_io:
            return

        # Vẽ 2 chart trên cùng 1 figure
        fig = self.canvas_cmp.fig
        fig.clear()

        all_ivs = [
            (self.intervals_cpu, 'CPU-bound'),
            (self.intervals_io,  'I/O-bound'),
        ]
        for i, (ivs, title) in enumerate(all_ivs):
            if not ivs:
                continue
            ax    = fig.add_subplot(1, 2, i+1)
            pids  = sorted(set(iv['pid'] for iv in ivs))
            pidx  = {pid: j for j, pid in enumerate(pids)}
            t_min = min(iv['start'] for iv in ivs)
            t_max = max(iv['end']   for iv in ivs)
            span  = max(t_max - t_min, 1)

            for iv in ivs:
                y   = pidx[iv['pid']]
                dur = iv['end'] - iv['start']
                if dur <= 0: continue
                ax.broken_barh(
                    [(iv['start'], dur)], (y-0.38, 0.76),
                    facecolors=STATE_COLORS.get(iv['state'], '#888'),
                    edgecolors='white', linewidth=0.4, alpha=0.88
                )
            ax.set_yticks(range(len(pids)))
            ax.set_yticklabels([f'PID {p}' for p in pids], fontsize=9)
            ax.set_xlabel('CPU Ticks')
            ax.set_title(title, fontweight='bold')
            ax.invert_yaxis()
            ax.grid(axis='x', linestyle='--', alpha=0.3)

        fig.tight_layout()
        self.canvas_cmp.draw()

        # Update stats table
        self.stats_table.update_stats(self.stats_cpu, self.stats_io)
        self.tabs.setCurrentIndex(2)

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Lưu PNG', os.path.expanduser('~/viz/export.png'),
            'PNG (*.png)'
        )
        if not path:
            return
        idx = self.tabs.currentIndex()
        canvas = [self.canvas_cpu, self.canvas_io, self.canvas_cmp][idx]
        canvas.fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f'Exported: {path}')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
