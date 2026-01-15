import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from PIL import Image, ImageTk

SUPPORTED_EXTENSIONS = (".tif", ".tiff")


def build_prefix_groups(folder_path: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for entry in os.listdir(folder_path):
        lower_name = entry.lower()
        if not lower_name.endswith(SUPPORTED_EXTENSIONS):
            continue
        full_path = os.path.join(folder_path, entry)
        if not os.path.isfile(full_path):
            continue
        stem, _ = os.path.splitext(entry)
        prefix = stem.rsplit("_", 1)[0] if "_" in stem else stem
        groups.setdefault(prefix, []).append(full_path)
    for paths in groups.values():
        paths.sort()
    return groups


class TiffViewerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MicaSense Tiff Viewer")
        self.root.geometry("1200x800")

        self.folder_path = tk.StringVar(value="未選擇資料夾")
        self.prefix_groups: list[tuple[str, list[str]]] = []
        self.photo_refs: list[ImageTk.PhotoImage | None] = [None] * 8
        self.colorbar_refs: list[ImageTk.PhotoImage | None] = [None] * 8

        self.band_slots = [
            {"label": "藍光 475", "keywords": ("475", "blue")},
            {"label": "綠光 560", "keywords": ("560", "green")},
            {"label": "紅光 668", "keywords": ("668", "red")},
            {"label": "紅邊 717", "keywords": ("717", "rededge", "red-edge")},
            {"label": "近紅外 842", "keywords": ("842", "nir")},
            {"label": "全色 634", "keywords": ("634", "pan", "panchromatic")},
            {"label": "LWIR 10.5 µm", "keywords": ("10.5", "10500", "lwir")},
            {"label": "（空白）", "keywords": ()},
        ]

        self._build_layout()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(container)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        right_frame = ttk.Frame(container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        select_button = ttk.Button(left_frame, text="指定資料夾", command=self.select_folder)
        select_button.pack(fill=tk.X)

        folder_label = ttk.Label(left_frame, textvariable=self.folder_path, wraplength=240)
        folder_label.pack(fill=tk.X, pady=(8, 12))

        list_label = ttk.Label(left_frame, text="前綴清單")
        list_label.pack(anchor=tk.W)

        self.prefix_list = tk.Listbox(left_frame, height=20)
        self.prefix_list.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self.prefix_list.bind("<<ListboxSelect>>", self.on_prefix_selected)

        nav_frame = ttk.Frame(left_frame)
        nav_frame.pack(fill=tk.X)

        prev_button = ttk.Button(nav_frame, text="上一張", command=self.select_previous)
        prev_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

        next_button = ttk.Button(nav_frame, text="下一張", command=self.select_next)
        next_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0))

        self.image_frame = ttk.Frame(right_frame)
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        for row in range(4):
            weight = 3 if row in (0, 2) else 1
            self.image_frame.rowconfigure(row, weight=weight)
        for column in range(4):
            self.image_frame.columnconfigure(column, weight=1)

        self.image_labels: list[ttk.Label] = []
        self.band_labels: list[ttk.Label] = []
        self.colorbar_labels: list[ttk.Label] = []
        for index, band in enumerate(self.band_slots):
            column = index % 4
            image_row = 0 if index < 4 else 2
            info_row = image_row + 1

            image_label = ttk.Label(
                self.image_frame,
                text=f"第 {index + 1} 格",
                anchor="center",
                relief="solid",
            )
            image_label.grid(row=image_row, column=column, sticky="nsew", padx=6, pady=6)

            info_frame = ttk.Frame(self.image_frame)
            info_frame.grid(row=info_row, column=column, sticky="nsew", padx=6, pady=(0, 6))

            band_label = ttk.Label(info_frame, text=band["label"], anchor="center")
            band_label.pack(fill=tk.X)

            colorbar_label = ttk.Label(info_frame)
            colorbar_label.pack(fill=tk.X, pady=(4, 0))

            self.image_labels.append(image_label)
            self.band_labels.append(band_label)
            self.colorbar_labels.append(colorbar_label)

    def _create_colorbar(self, width: int = 160, height: int = 14) -> ImageTk.PhotoImage:
        gradient = Image.new("RGB", (width, height))
        for x in range(width):
            value = int(255 * (x / max(width - 1, 1)))
            for y in range(height):
                gradient.putpixel((x, y), (value, value, value))
        return ImageTk.PhotoImage(gradient)

    def _order_paths_by_band(self, paths: list[str]) -> list[str | None]:
        ordered: list[str | None] = [None] * len(self.band_slots)
        used_paths: set[str] = set()
        lower_paths = [(path, os.path.basename(path).lower()) for path in paths]
        for index, band in enumerate(self.band_slots[:-1]):
            for path, name in lower_paths:
                if path in used_paths:
                    continue
                if any(keyword in name for keyword in band["keywords"]):
                    ordered[index] = path
                    used_paths.add(path)
                    break
        for index in range(len(self.band_slots) - 1):
            if ordered[index] is not None:
                continue
            for path in paths:
                if path in used_paths:
                    continue
                ordered[index] = path
                used_paths.add(path)
                break
        return ordered

    def select_folder(self) -> None:
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return
        self.folder_path.set(folder_path)
        groups = build_prefix_groups(folder_path)
        self.prefix_groups = [
            (prefix, paths)
            for prefix, paths in sorted(groups.items())
            if len(paths) == 7
        ]
        self.prefix_list.delete(0, tk.END)
        for prefix, paths in self.prefix_groups:
            self.prefix_list.insert(tk.END, f"{prefix} ({len(paths)})")
        if self.prefix_groups:
            self.prefix_list.selection_set(0)
            self.prefix_list.event_generate("<<ListboxSelect>>")
        else:
            self.clear_images()

    def clear_images(self) -> None:
        for index, label in enumerate(self.image_labels):
            label.configure(image="", text=f"第 {index + 1} 格")
        for label in self.colorbar_labels:
            label.configure(image="")
        self.photo_refs = [None] * 8
        self.colorbar_refs = [None] * 8

    def on_prefix_selected(self, _event: tk.Event) -> None:
        selection = self.prefix_list.curselection()
        if not selection:
            return
        index = selection[0]
        _, paths = self.prefix_groups[index]
        self.update_images(paths)

    def update_images(self, paths: list[str]) -> None:
        self.clear_images()
        ordered_paths = self._order_paths_by_band(paths)
        for idx, path in enumerate(ordered_paths):
            if idx >= len(self.band_slots):
                break
            if not path:
                self.image_labels[idx].configure(text="無影像")
                self.colorbar_labels[idx].configure(image="")
                continue
            image = Image.open(path)
            image.thumbnail((300, 200))
            photo = ImageTk.PhotoImage(image)
            self.photo_refs[idx] = photo
            self.image_labels[idx].configure(image=photo, text="")
            colorbar = self._create_colorbar()
            self.colorbar_refs[idx] = colorbar
            self.colorbar_labels[idx].configure(image=colorbar)

    def select_previous(self) -> None:
        selection = self.prefix_list.curselection()
        if not selection:
            return
        index = max(selection[0] - 1, 0)
        self.prefix_list.selection_clear(0, tk.END)
        self.prefix_list.selection_set(index)
        self.prefix_list.see(index)
        self.prefix_list.event_generate("<<ListboxSelect>>")

    def select_next(self) -> None:
        selection = self.prefix_list.curselection()
        if not selection:
            return
        index = min(selection[0] + 1, len(self.prefix_groups) - 1)
        self.prefix_list.selection_clear(0, tk.END)
        self.prefix_list.selection_set(index)
        self.prefix_list.see(index)
        self.prefix_list.event_generate("<<ListboxSelect>>")


if __name__ == "__main__":
    app_root = tk.Tk()
    app = TiffViewerApp(app_root)
    app_root.mainloop()
