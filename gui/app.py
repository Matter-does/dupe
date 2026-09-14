"""Lightweight GUI shell application for dupe.

Utilizes Python 3 standard library tkinter and ttk to provide a clean,
responsive, non-blocking interface over the authoritative J2 dupe engine.
"""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any

from gui.adapter import EngineAdapter, EngineResult
from gui.view_models import (
    ChecksumViewModel,
    DuplicateViewModel,
    format_bytes,
)


class DupeApp:
    """Main desktop application window for the dupe GUI shell."""

    def __init__(
        self,
        root: tk.Tk | None = None,
        *,
        adapter: EngineAdapter | None = None,
        initial_path: str = "",
        initial_workload: str = "duplicate",
    ) -> None:
        self.root = root if root is not None else tk.Tk()
        self.adapter = adapter or EngineAdapter()

        self.root.title("dupe — Filesystem Intelligence Engine")
        self.root.geometry("900x680")
        self.root.minsize(800, 560)

        # Reactive Tkinter state variables
        self.path_var = tk.StringVar(value=initial_path)
        self.workload_var = tk.StringVar(value=initial_workload)
        self.status_var = tk.StringVar(value="Ready. Select a directory to analyze.")
        self.is_running = False

        # Resolve engine mode to display in UI header
        try:
            mode_tuple = self.adapter.resolve_engine_mode()
            if isinstance(mode_tuple, (tuple, list)) and len(mode_tuple) >= 1:
                self.engine_mode = str(mode_tuple[0])
            else:
                self.engine_mode = "unavailable"
        except Exception:
            self.engine_mode = "unavailable"

        # Metrics display variables
        self.metric_1_title = tk.StringVar(value="Files Scanned")
        self.metric_1_val = tk.StringVar(value="—")
        self.metric_2_title = tk.StringVar(value="Hash Candidates")
        self.metric_2_val = tk.StringVar(value="—")
        self.metric_3_title = tk.StringVar(value="Duplicate Groups")
        self.metric_3_val = tk.StringVar(value="—")
        self.metric_4_title = tk.StringVar(value="Reclaimable Space")
        self.metric_4_val = tk.StringVar(value="—")
        self.workload_desc_var = tk.StringVar(value="")

        # Current view models
        self.last_result: EngineResult | None = None
        self.last_duplicate_vm: DuplicateViewModel | None = None
        self.last_checksum_vm: ChecksumViewModel | None = None

        self._configure_styles()
        self._build_ui()
        self._on_workload_change()

    def _configure_styles(self) -> None:
        """Set up unified ttk styling."""
        self.style = ttk.Style(self.root)
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        # Configure custom typography & palette
        self.style.configure("TFrame", background="#f8f9fa")
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), background="#f8f9fa", foreground="#212529")
        self.style.configure("SubHeader.TLabel", font=("Helvetica", 9), background="#f8f9fa", foreground="#6c757d")
        self.style.configure("EngineBadge.TLabel", font=("Helvetica", 8, "bold"), background="#e7f1ff", foreground="#0d6efd", padding=4)
        self.style.configure("Desc.TLabel", font=("Helvetica", 8, "italic"), background="#f8f9fa", foreground="#495057")
        self.style.configure("Section.TLabelframe", background="#f8f9fa", padding=10)
        self.style.configure("Section.TLabelframe.Label", font=("Helvetica", 10, "bold"), foreground="#495057")

        # Metric badges
        self.style.configure("MetricTitle.TLabel", font=("Helvetica", 8, "bold"), foreground="#6c757d", background="#ffffff")
        self.style.configure("MetricVal.TLabel", font=("Helvetica", 13, "bold"), foreground="#0d6efd", background="#ffffff")

        # Action button
        self.style.configure("Action.TButton", font=("Helvetica", 10, "bold"), padding=6)
        self.style.configure("Treeview", font=("Helvetica", 9), rowheight=24)
        self.style.configure("Treeview.Heading", font=("Helvetica", 9, "bold"))

    def _build_ui(self) -> None:
        """Construct visual widget hierarchy."""
        main_container = ttk.Frame(self.root, padding=14)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header Frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_row = ttk.Frame(header_frame)
        title_row.pack(fill=tk.X)

        title_lbl = ttk.Label(title_row, text="dupe — Filesystem Intelligence Engine", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)

        if self.engine_mode == "native":
            engine_desc = "J2 Native (build/dupe)"
        elif self.engine_mode == "interpreter":
            engine_desc = "J2 Interpreter (j2)"
        else:
            engine_desc = "Unavailable"
        self.engine_badge = ttk.Label(
            title_row,
            text=f"Engine: {engine_desc}",
            style="EngineBadge.TLabel",
        )
        self.engine_badge.pack(side=tk.RIGHT)

        sub_lbl = ttk.Label(
            header_frame,
            text="Lightweight native desktop shell delegating to the verified J2 analysis engine.",
            style="SubHeader.TLabel",
        )
        sub_lbl.pack(anchor=tk.W, pady=(2, 0))

        # 2. Controls Section (Path & Workload)
        controls_group = ttk.LabelFrame(main_container, text="Configuration & Target", style="Section.TLabelframe")
        controls_group.pack(fill=tk.X, pady=(0, 10))

        # Path input row
        path_row = ttk.Frame(controls_group)
        path_row.pack(fill=tk.X, pady=(2, 6))

        path_lbl = ttk.Label(path_row, text="Target Directory:", width=16, font=("Helvetica", 9, "bold"))
        path_lbl.pack(side=tk.LEFT)

        self.path_entry = ttk.Entry(path_row, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.demo_btn = ttk.Button(path_row, text="Load Demo Corpus", command=self.on_load_demo_corpus)
        self.demo_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.browse_btn = ttk.Button(path_row, text="Browse...", command=self.on_browse)
        self.browse_btn.pack(side=tk.RIGHT)

        # Workload selection row
        workload_row = ttk.Frame(controls_group)
        workload_row.pack(fill=tk.X, pady=(4, 2))

        wk_lbl = ttk.Label(workload_row, text="Workload Mode:", width=16, font=("Helvetica", 9, "bold"))
        wk_lbl.pack(side=tk.LEFT)

        self.rb_dup = ttk.Radiobutton(
            workload_row,
            text="Exact Duplicate Scan (find duplicates & reclaimable bytes)",
            value="duplicate",
            variable=self.workload_var,
            command=self._on_workload_change,
        )
        self.rb_dup.pack(side=tk.LEFT, padx=(0, 16))

        self.rb_chk = ttk.Radiobutton(
            workload_row,
            text="Checksum Inventory (SHA-256 ledger of regular files)",
            value="checksum",
            variable=self.workload_var,
            command=self._on_workload_change,
        )
        self.rb_chk.pack(side=tk.LEFT)

        # Workload description note
        self.workload_desc_lbl = ttk.Label(
            controls_group,
            textvariable=self.workload_desc_var,
            style="Desc.TLabel",
            wraplength=800,
        )
        self.workload_desc_lbl.pack(anchor=tk.W, padx=(2, 0), pady=(4, 2))

        # 3. Action & Status Bar Frame
        action_row = ttk.Frame(main_container)
        action_row.pack(fill=tk.X, pady=(0, 10))

        self.analyze_btn = ttk.Button(
            action_row,
            text="Analyze Directory",
            style="Action.TButton",
            command=self.on_analyze,
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 12))

        self.progress_bar = ttk.Progressbar(action_row, mode="indeterminate", length=140)
        # progress bar packed only during active analysis

        self.status_lbl = ttk.Label(action_row, textvariable=self.status_var, font=("Helvetica", 9, "italic"))
        self.status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # 4. Summary Metric Cards
        self.metrics_container = ttk.Frame(main_container)
        self.metrics_container.pack(fill=tk.X, pady=(0, 10))
        self._build_metric_cards()

        # 5. Error Banner (hidden by default)
        self.error_frame = tk.Frame(main_container, bg="#f8d7da", relief=tk.SOLID, borderwidth=1, padx=8, pady=6)
        self.error_lbl = tk.Label(
            self.error_frame,
            text="",
            bg="#f8d7da",
            fg="#842029",
            font=("Helvetica", 9, "bold"),
            justify=tk.LEFT,
            wraplength=820,
        )
        self.error_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.error_dismiss_btn = ttk.Button(self.error_frame, text="Dismiss", command=self._hide_error)
        self.error_dismiss_btn.pack(side=tk.RIGHT, padx=(6, 0))

        # 6. Results Table / Tree Area
        results_group = ttk.LabelFrame(main_container, text="Analysis Results", style="Section.TLabelframe")
        results_group.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(results_group)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview with both scrollbars
        self.tree = ttk.Treeview(table_frame, selectmode="browse")
        self.v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

    def _build_metric_cards(self) -> None:
        """Create structured 4-column summary metric cards."""
        card_configs = [
            (self.metric_1_title, self.metric_1_val),
            (self.metric_2_title, self.metric_2_val),
            (self.metric_3_title, self.metric_3_val),
            (self.metric_4_title, self.metric_4_val),
        ]
        self.metrics_container.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric_cols")

        for idx, (t_var, v_var) in enumerate(card_configs):
            card = tk.Frame(self.metrics_container, bg="#ffffff", relief=tk.SOLID, borderwidth=1, padx=10, pady=8)
            card.grid(row=0, column=idx, sticky="nsew", padx=4)

            lbl_t = ttk.Label(card, textvariable=t_var, style="MetricTitle.TLabel")
            lbl_t.pack(anchor=tk.W)

            lbl_v = ttk.Label(card, textvariable=v_var, style="MetricVal.TLabel")
            lbl_v.pack(anchor=tk.W, pady=(2, 0))

    def _on_workload_change(self) -> None:
        """Update column configurations and labels when workload changes."""
        mode = self.workload_var.get()
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        self._hide_error()

        if mode == "duplicate":
            self.workload_desc_var.set(
                "Exact Duplicate Scan: Discovers files, prefilters by size, hashes candidates with SHA-256, "
                "groups duplicate clusters, and reports reclaimable storage."
            )
            self.metric_1_title.set("Files Scanned")
            self.metric_2_title.set("Hash Candidates")
            self.metric_3_title.set("Duplicate Groups")
            self.metric_4_title.set("Reclaimable Space")

            self.tree["show"] = "tree headings"
            self.tree["columns"] = ("size", "reclaimable", "hash")
            self.tree.heading("#0", text="Duplicate Group / Path", anchor=tk.W)
            self.tree.heading("size", text="File Size", anchor=tk.E)
            self.tree.heading("reclaimable", text="Reclaimable Bytes", anchor=tk.E)
            self.tree.heading("hash", text="SHA-256 Digest", anchor=tk.W)

            self.tree.column("#0", width=420, stretch=True)
            self.tree.column("size", width=120, anchor=tk.E)
            self.tree.column("reclaimable", width=140, anchor=tk.E)
            self.tree.column("hash", width=220, stretch=True)

            if self.last_duplicate_vm:
                self._render_duplicate_results(self.last_duplicate_vm)
            else:
                self._reset_metrics()

        elif mode == "checksum":
            self.workload_desc_var.set(
                "Checksum Inventory: Discovers all regular files and produces a comprehensive cryptographic "
                "SHA-256 audit ledger."
            )
            self.metric_1_title.set("Total Regular Files")
            self.metric_2_title.set("Total Scanned Bytes")
            self.metric_3_title.set("Ledger Entries")
            self.metric_4_title.set("Ledger Status")

            self.tree["show"] = "headings"
            self.tree["columns"] = ("idx", "path", "size", "sha256")
            self.tree.heading("idx", text="#", anchor=tk.CENTER)
            self.tree.heading("path", text="File Path", anchor=tk.W)
            self.tree.heading("size", text="Size", anchor=tk.E)
            self.tree.heading("sha256", text="SHA-256 Checksum", anchor=tk.W)

            self.tree.column("idx", width=50, anchor=tk.CENTER)
            self.tree.column("path", width=460, stretch=True)
            self.tree.column("size", width=120, anchor=tk.E)
            self.tree.column("sha256", width=270, stretch=True)

            if self.last_checksum_vm:
                self._render_checksum_results(self.last_checksum_vm)
            else:
                self._reset_metrics()

    def _reset_metrics(self) -> None:
        self.metric_1_val.set("—")
        self.metric_2_val.set("—")
        self.metric_3_val.set("—")
        self.metric_4_val.set("—")

    def on_browse(self) -> None:
        """Open native directory selection dialog."""
        selected = filedialog.askdirectory(title="Select Directory to Analyze")
        if selected:
            self.set_target_path(selected)

    def on_load_demo_corpus(self) -> None:
        """Helper to quickly load or generate the deterministic demo corpus."""
        demo_dir = Path("demo_corpus").resolve()
        if not demo_dir.exists():
            try:
                from tests.demo_corpus import create_demo_corpus
                create_demo_corpus(demo_dir)
            except Exception:
                pass
        self.set_target_path(str(demo_dir))
        self.status_var.set(f"Demo corpus loaded: {demo_dir} (8 regular files, 5,258 total bytes)")

    def set_target_path(self, path_str: str) -> None:
        """Programmatically set the target directory path."""
        norm_path = str(Path(path_str).resolve()) if path_str else ""
        self.path_var.set(norm_path)
        self.status_var.set(f"Target selected: {norm_path}")

    def set_workload(self, workload: str) -> None:
        """Programmatically set workload mode ('duplicate' or 'checksum')."""
        if workload in ("duplicate", "checksum"):
            self.workload_var.set(workload)
            self._on_workload_change()

    def on_analyze(self) -> None:
        """Handle Analyze button click and launch background engine execution."""
        if self.is_running:
            return

        target_path = self.path_var.get().strip()
        if not target_path:
            self._show_error("Please specify or browse for a target directory to analyze.")
            return

        workload = self.workload_var.get()
        self._set_running_state(True)
        self._hide_error()
        self.status_var.set(f"Analyzing '{target_path}' using workload '{workload}'... Please wait.")

        # Delegate execution to background thread via EngineAdapter
        self.adapter.run_analysis_async(
            workload,
            target_path,
            on_complete=self._threadsafe_complete,
        )

    def _threadsafe_complete(self, result: EngineResult) -> None:
        """Thread-safe callback dispatching results to the main Tk event loop."""
        self.root.after(0, lambda: self._apply_engine_result(result))

    def _apply_engine_result(self, result: EngineResult) -> None:
        """Process and present engine results on the main UI thread."""
        self.last_result = result
        self._set_running_state(False)

        if not result.success:
            err_msg = result.error_message or "Unknown engine error occurred."
            self.status_var.set(f"Analysis failed (exit code {result.returncode}) after {result.duration_seconds:.2f}s")
            self._show_error(f"Engine Error (Exit {result.returncode}):\n{err_msg}")
            self._reset_metrics()
            self.tree.delete(*self.tree.get_children())
            return

        # Render successful results
        data = result.data or {}
        try:
            if result.workload == "duplicate":
                vm = DuplicateViewModel.from_engine_data(data)
                self.last_duplicate_vm = vm
                self._render_duplicate_results(vm)
                self.status_var.set(
                    f"Duplicate scan complete in {result.duration_seconds:.2f}s. "
                    f"Scanned {vm.files_scanned} files, found {vm.duplicate_groups_count} duplicate groups."
                )
            elif result.workload == "checksum":
                vm = ChecksumViewModel.from_engine_data(data)
                self.last_checksum_vm = vm
                self._render_checksum_results(vm)
                self.status_var.set(
                    f"Checksum inventory complete in {result.duration_seconds:.2f}s. "
                    f"Enumerated {vm.total_files} files ({vm.total_bytes_formatted})."
                )
        except Exception as exc:
            self._set_running_state(False)
            self.last_duplicate_vm = None
            self.last_checksum_vm = None
            self.status_var.set(f"UI presentation error: {exc}")
            self._show_error(f"UI Presentation Error:\nFailed to render engine output: {exc}")
            self._reset_metrics()
            self.tree.delete(*self.tree.get_children())
            return

    def _render_duplicate_results(self, vm: DuplicateViewModel) -> None:
        """Populate UI widgets with DuplicateViewModel data."""
        self.metric_1_val.set(f"{vm.files_scanned:,}")
        self.metric_2_val.set(f"{vm.hash_candidates:,}")
        self.metric_3_val.set(f"{vm.duplicate_groups_count:,}")
        self.metric_4_val.set(vm.reclaimable_formatted)

        self.tree.delete(*self.tree.get_children())
        for group in vm.groups:
            group_label = f"Group {group.group_index}: {group.file_count} files"
            parent_node = self.tree.insert(
                "",
                tk.END,
                text=group_label,
                values=(group.size_formatted, group.reclaimable_formatted, group.digest),
                open=True,
            )
            for file_path in group.files:
                self.tree.insert(
                    parent_node,
                    tk.END,
                    text=f"  📄 {file_path}",
                    values=(group.size_formatted, "", ""),
                )

    def _render_checksum_results(self, vm: ChecksumViewModel) -> None:
        """Populate UI widgets with ChecksumViewModel data."""
        self.metric_1_val.set(f"{vm.total_files:,}")
        self.metric_2_val.set(vm.total_bytes_formatted)
        self.metric_3_val.set(f"{len(vm.entries):,}")
        self.metric_4_val.set("Verified SHA-256")

        self.tree.delete(*self.tree.get_children())
        for entry in vm.entries:
            self.tree.insert(
                "",
                tk.END,
                values=(entry.index, entry.path, entry.size_formatted, entry.sha256),
            )

    def _set_running_state(self, running: bool) -> None:
        """Toggle interactive widget states during background processing."""
        self.is_running = running
        if running:
            self.analyze_btn.configure(state=tk.DISABLED)
            self.browse_btn.configure(state=tk.DISABLED)
            self.demo_btn.configure(state=tk.DISABLED)
            self.path_entry.configure(state=tk.DISABLED)
            self.rb_dup.configure(state=tk.DISABLED)
            self.rb_chk.configure(state=tk.DISABLED)
            self.progress_bar.pack(side=tk.LEFT, padx=(0, 8))
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.analyze_btn.configure(state=tk.NORMAL)
            self.browse_btn.configure(state=tk.NORMAL)
            self.demo_btn.configure(state=tk.NORMAL)
            self.path_entry.configure(state=tk.NORMAL)
            self.rb_dup.configure(state=tk.NORMAL)
            self.rb_chk.configure(state=tk.NORMAL)

    def _show_error(self, message: str) -> None:
        self.error_lbl.configure(text=message)
        self.error_frame.pack(fill=tk.X, pady=(0, 10))

    def _hide_error(self) -> None:
        self.error_frame.pack_forget()
        self.error_lbl.configure(text="")

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
