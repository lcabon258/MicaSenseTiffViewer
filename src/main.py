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

    def _create_colorbar(
        self,
        width: int,
        height: int,
        is_lwir: bool,
    ) -> ImageTk.PhotoImage:
        gradient = [x / max(width - 1, 1) for x in range(width)]
        if is_lwir:
            lut = self._inferno_lut()
            row = [lut[int(value * (len(lut) - 1))] for value in gradient]
        else:
            row = [
                (value, value, value)
                for value in (int(value * 255) for value in gradient)
            ]
        data = row * height
        colorbar = Image.new("RGB", (width, height))
        colorbar.putdata(data)
        return ImageTk.PhotoImage(colorbar)

    def _apply_colormap(
        self,
        normalized: list[float],
        size: tuple[int, int],
        is_lwir: bool,
    ) -> Image.Image:
        clipped = [min(max(value, 0.0), 1.0) for value in normalized]
        if is_lwir:
            lut = self._inferno_lut()
            data = [lut[int(value * (len(lut) - 1))] for value in clipped]
        else:
            data = [
                (value, value, value)
                for value in (int(value * 255) for value in clipped)
            ]
        image = Image.new("RGB", size)
        image.putdata(data)
        return image

    def _inferno_lut(self) -> list[tuple[int, int, int]]:
        return [
            (0, 0, 4),
                (1, 0, 5),
                (1, 1, 6),
                (1, 1, 8),
                (2, 1, 10),
                (2, 2, 12),
                (2, 2, 14),
                (3, 2, 16),
                (4, 3, 18),
                (4, 3, 20),
                (5, 4, 22),
                (6, 4, 24),
                (6, 5, 26),
                (7, 5, 29),
                (8, 6, 31),
                (9, 6, 33),
                (10, 7, 35),
                (11, 7, 38),
                (12, 8, 40),
                (13, 8, 42),
                (14, 9, 45),
                (15, 9, 47),
                (16, 10, 50),
                (17, 11, 52),
                (18, 11, 55),
                (20, 12, 58),
                (21, 12, 60),
                (22, 13, 63),
                (23, 14, 66),
                (24, 14, 68),
                (26, 15, 71),
                (27, 15, 74),
                (28, 16, 77),
                (29, 17, 80),
                (31, 17, 82),
                (32, 18, 85),
                (33, 19, 88),
                (35, 19, 91),
                (36, 20, 94),
                (38, 21, 97),
                (39, 21, 100),
                (41, 22, 103),
                (42, 23, 106),
                (44, 23, 109),
                (45, 24, 112),
                (47, 25, 115),
                (48, 26, 118),
                (50, 26, 121),
                (52, 27, 124),
                (53, 28, 127),
                (55, 29, 130),
                (57, 30, 133),
                (58, 30, 136),
                (60, 31, 139),
                (62, 32, 142),
                (64, 33, 145),
                (66, 34, 148),
                (67, 35, 151),
                (69, 36, 154),
                (71, 36, 157),
                (73, 37, 160),
                (75, 38, 163),
                (77, 39, 166),
                (79, 40, 168),
                (81, 41, 171),
                (83, 42, 174),
                (85, 43, 176),
                (87, 44, 179),
                (89, 45, 181),
                (91, 46, 184),
                (93, 47, 186),
                (95, 48, 189),
                (98, 49, 191),
                (100, 50, 193),
                (102, 51, 195),
                (104, 52, 197),
                (107, 53, 199),
                (109, 54, 201),
                (111, 55, 203),
                (114, 56, 205),
                (116, 57, 207),
                (118, 58, 208),
                (121, 60, 210),
                (123, 61, 211),
                (125, 62, 212),
                (128, 63, 213),
                (130, 64, 214),
                (133, 66, 215),
                (135, 67, 215),
                (138, 68, 216),
                (140, 69, 217),
                (143, 71, 217),
                (145, 72, 218),
                (148, 73, 218),
                (150, 75, 218),
                (153, 76, 219),
                (155, 77, 219),
                (158, 79, 219),
                (160, 80, 219),
                (163, 81, 219),
                (165, 83, 219),
                (168, 84, 219),
                (170, 85, 219),
                (173, 87, 219),
                (175, 88, 219),
                (178, 90, 219),
                (180, 91, 219),
                (183, 92, 218),
                (185, 94, 218),
                (188, 95, 218),
                (190, 97, 218),
                (193, 98, 217),
                (195, 100, 217),
                (198, 101, 217),
                (200, 103, 216),
                (202, 104, 216),
                (205, 106, 215),
                (207, 107, 215),
                (210, 109, 214),
                (212, 110, 214),
                (214, 112, 213),
                (217, 113, 212),
                (219, 115, 212),
                (221, 116, 211),
                (224, 118, 210),
                (226, 119, 210),
                (228, 121, 209),
                (231, 122, 208),
                (233, 124, 207),
                (235, 125, 207),
                (238, 127, 206),
                (240, 128, 205),
                (242, 130, 204),
                (245, 131, 203),
                (247, 133, 202),
                (249, 134, 201),
                (251, 136, 200),
                (254, 137, 199),
                (255, 139, 198),
                (255, 140, 197),
                (255, 142, 196),
                (255, 143, 195),
                (255, 145, 194),
                (255, 146, 193),
                (255, 148, 191),
                (255, 149, 190),
                (255, 151, 189),
                (255, 152, 188),
                (255, 154, 186),
                (255, 155, 185),
                (255, 157, 184),
                (255, 158, 183),
                (255, 160, 181),
                (255, 161, 180),
                (255, 163, 179),
                (255, 164, 177),
                (255, 166, 176),
                (255, 168, 175),
                (255, 169, 173),
                (255, 171, 172),
                (255, 172, 170),
                (255, 174, 169),
                (255, 175, 167),
                (255, 177, 166),
                (255, 179, 164),
                (255, 180, 163),
                (255, 182, 161),
                (255, 184, 160),
                (255, 185, 158),
                (255, 187, 157),
                (255, 189, 155),
                (255, 190, 154),
                (255, 192, 152),
                (255, 194, 151),
                (255, 195, 149),
                (255, 197, 148),
                (255, 199, 146),
                (255, 200, 145),
                (255, 202, 143),
                (255, 204, 142),
                (255, 205, 140),
                (255, 207, 139),
                (255, 209, 137),
                (255, 210, 136),
                (255, 212, 134),
                (255, 214, 133),
                (255, 215, 131),
                (255, 217, 130),
                (255, 219, 128),
                (255, 220, 127),
                (255, 222, 125),
                (255, 224, 124),
                (255, 225, 122),
                (255, 227, 121),
                (255, 229, 119),
                (255, 230, 118),
                (255, 232, 116),
                (255, 234, 115),
                (255, 235, 113),
                (255, 237, 112),
                (255, 239, 110),
                (255, 240, 109),
                (255, 242, 107),
                (255, 244, 106),
                (255, 245, 104),
                (255, 247, 103),
                (255, 249, 101),
                (255, 250, 100),
                (255, 252, 98),
                (255, 254, 97),
                (252, 255, 96),
                (248, 255, 96),
                (244, 255, 96),
                (240, 255, 96),
                (236, 255, 96),
                (232, 255, 96),
                (228, 255, 96),
                (224, 255, 96),
                (220, 255, 96),
                (216, 255, 96),
                (212, 255, 96),
                (208, 255, 96),
                (204, 255, 96),
                (200, 255, 96),
                (196, 255, 96),
                (192, 255, 96),
                (188, 255, 96),
                (184, 255, 96),
                (180, 255, 96),
                (176, 255, 96),
                (172, 255, 96),
                (168, 255, 96),
                (164, 255, 96),
                (160, 255, 96),
                (156, 255, 96),
                (152, 255, 96),
                (148, 255, 96),
                (144, 255, 96),
                (140, 255, 96),
                (136, 255, 96),
                (132, 255, 96),
            (128, 255, 96),
        ]

    def _load_tiff_data(self, path: str) -> tuple[list[float], tuple[int, int], float, float]:
        with Image.open(path) as image:
            float_image = image.convert("F")
            data = list(float_image.getdata())
        min_value = min(data) if data else 0.0
        max_value = max(data) if data else 0.0
        return data, float_image.size, min_value, max_value

    def _normalize(self, data: list[float], min_value: float, max_value: float) -> list[float]:
        if max_value <= min_value:
            return [0.0 for _ in data]
        scale = 1.0 / (max_value - min_value)
        return [(value - min_value) * scale for value in data]

    def _fit_image_to_label(self, image: Image.Image, label: ttk.Label) -> Image.Image:
        target_width = label.winfo_width()
        target_height = label.winfo_height()
        if target_width < 10 or target_height < 10:
            target_width = 300
            target_height = 200
        scale = min(target_width / image.width, target_height / image.height)
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        return image.resize(new_size, resample=Image.Resampling.LANCZOS)

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
        self.root.update_idletasks()
        ordered_paths = self._order_paths_by_band(paths)
        for idx, path in enumerate(ordered_paths):
            if idx >= len(self.band_slots):
                break
            if not path:
                self.image_labels[idx].configure(text="無影像")
                self.colorbar_labels[idx].configure(image="")
                continue
            is_lwir = "lwir" in self.band_slots[idx]["keywords"]
            data, size, min_value, max_value = self._load_tiff_data(path)
            normalized = self._normalize(data, min_value, max_value)
            display_image = self._apply_colormap(normalized, size, is_lwir=is_lwir)
            fitted_image = self._fit_image_to_label(display_image, self.image_labels[idx])
            photo = ImageTk.PhotoImage(fitted_image)
            self.photo_refs[idx] = photo
            self.image_labels[idx].configure(image=photo, text="")
            colorbar = self._create_colorbar(width=160, height=14, is_lwir=is_lwir)
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
