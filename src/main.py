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
        self.photo_refs: list[ImageTk.PhotoImage | None] = [None] * 7

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

        self.image_labels: list[ttk.Label] = []
        for index in range(7):
            label = ttk.Label(self.image_frame, text=f"第 {index + 1} 張")
            label.grid(row=index, column=0, sticky="w", pady=6)
            image_label = ttk.Label(self.image_frame)
            image_label.grid(row=index, column=1, sticky="w", padx=(12, 0), pady=6)
            self.image_labels.append(image_label)

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
        for label in self.image_labels:
            label.configure(image="", text="")
        self.photo_refs = [None] * 7

    def on_prefix_selected(self, _event: tk.Event) -> None:
        selection = self.prefix_list.curselection()
        if not selection:
            return
        index = selection[0]
        _, paths = self.prefix_groups[index]
        self.update_images(paths)

    def update_images(self, paths: list[str]) -> None:
        self.clear_images()
        for idx, path in enumerate(paths[:7]):
            image = Image.open(path)
            image.thumbnail((400, 200))
            photo = ImageTk.PhotoImage(image)
            self.photo_refs[idx] = photo
            self.image_labels[idx].configure(image=photo)

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
