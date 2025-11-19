import tkinter as tk
from tkinter import messagebox, ttk
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.image as mpimg

class RoadMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторна робота 5: Навігатор Україною")
        self.root.geometry("1400x900")

        self.graph = nx.Graph()
        self.pos = {} 
        
        # Параметри фону
        self.bg_x = 0.0
        self.bg_y = 0.0
        self.bg_scale = 1.0
        self.background_image_path = "ukraine_map.png" 
        self.bg_image = None

        self.load_full_data()
        self.create_widgets()
        self.load_background_image()
        self.draw_graph()

        # Події миші
        self.dragging_node = None
        self.cid_press = self.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_motion = self.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_release = self.figure.canvas.mpl_connect('button_release_event', self.on_release)

    def load_full_data(self):
        # Базові зв'язки (можна редагувати через інтерфейс)
        roads = [
            ("Ужгород", "Мукачево", 40), ("Мукачево", "Іршава", 25), 
            ("Мукачево", "Львів", 220), ("Львів", "Тернопіль", 128), 
            ("Львів", "Івано-Франківськ", 134), ("Львів", "Луцьк", 152), 
            ("Львів", "Рівне", 211), ("Луцьк", "Рівне", 75), 
            ("Луцьк", "Ковель", 65), ("Ковель", "Сарни", 130), 
            ("Сарни", "Коростень", 100), ("Рівне", "Житомир", 189), 
            ("Тернопіль", "Хмельницький", 112), ("Тернопіль", "Рівне", 160),
            ("Тернопіль", "Чернівці", 175), ("Івано-Франківськ", "Чернівці", 135),
            ("Хмельницький", "Вінниця", 120), ("Хмельницький", "Житомир", 155),
            ("Житомир", "Київ", 141), ("Житомир", "Вінниця", 129),
            ("Вінниця", "Умань", 160), ("Вінниця", "Біла Церква", 125),
            ("Київ", "Біла Церква", 85), ("Київ", "Чернігів", 149),
            ("Київ", "Черкаси", 192), ("Київ", "Пирятин", 155),
            ("Біла Церква", "Умань", 125), ("Черкаси", "Сміла", 30),
            ("Сміла", "Кропивницький", 105), ("Сміла", "Умань", 155),
            ("Черкаси", "Кременчук", 130), ("Умань", "Кропивницький", 168),
            ("Умань", "Одеса", 271), ("Умань", "Первомайськ", 85),
            ("Кропивницький", "Кривий Ріг", 120), ("Кропивницький", "Дніпро", 180),
            ("Кропивницький", "Олександрія", 75),
            ("Чернігів", "Суми", 180), ("Суми", "Харків", 185), ("Чернігів", "Прилуки", 130),
            ("Пирятин", "Полтава", 185), ("Полтава", "Харків", 145),
            ("Полтава", "Кременчук", 115), ("Полтава", "Дніпро", 195),
            ("Харків", "Дніпро", 220), ("Харків", "Ізюм", 125),
            ("Дніпро", "Запоріжжя", 86), ("Дніпро", "Кривий Ріг", 145),
            ("Дніпро", "Донецьк", 250), ("Дніпро", "Кам'янське", 40), ("Дніпро", "Павлоград", 75),
            ("Одеса", "Миколаїв", 133), ("Миколаїв", "Херсон", 71),
            ("Первомайськ", "Миколаїв", 165), ("Херсон", "Мелітополь", 230),
            ("Херсон", "Сімферополь", 280), 
            ("Запоріжжя", "Мелітополь", 120), ("Запоріжжя", "Маріуполь", 225),
            ("Мелітополь", "Маріуполь", 170), ("Мелітополь", "Сімферополь", 240),
            ("Ізюм", "Слов'янськ", 50), ("Слов'янськ", "Донецьк", 110),
            ("Слов'янськ", "Луганськ", 160), ("Донецьк", "Луганськ", 150),
            ("Донецьк", "Маріуполь", 115), ("Луганськ", "Ізварине", 60),
            ("Сімферополь", "Севастополь", 80), ("Сімферополь", "Ялта", 85), 
            ("Сімферополь", "Керч", 210), ("Севастополь", "Ялта", 80),
            ("Конотоп", "Суми", 120), ("Конотоп", "Чернігів", 150)
        ]
        for u, v, w in roads:
            self.graph.add_edge(u, v, weight=w)

        self.pos = {
          "Ужгород": (0.010, 0.549),
          "Мукачево": (0.044, 0.548),
          "Іршава": (0.075, 0.486),
          "Львів": (0.114, 0.683),
          "Івано-Франківськ": (0.139, 0.567),
          "Тернопіль": (0.192, 0.635),
          "Чернівці": (0.204, 0.475),
          "Луцьк": (0.188, 0.785),
          "Рівне": (0.235, 0.760),
          "Ковель": (0.167, 0.837),
          "Сарни": (0.261, 0.867),
          "Коростень": (0.363, 0.801),
          "Хмельницький": (0.271, 0.612),
          "Кам'янець-Подільський": (0.286, 0.515),
          "Житомир": (0.363, 0.708),
          "Вінниця": (0.350, 0.579),
          "Біла Церква": (0.446, 0.654),
          "Київ": (0.450, 0.730),
          "Чернігів": (0.560, 0.900),
          "Прилуки": (0.566, 0.754),
          "Черкаси": (0.538, 0.605),
          "Сміла": (0.506, 0.598),
          "Умань": (0.448, 0.530),
          "Кропивницький": (0.555, 0.499),
          "Олександрія": (0.605, 0.526),
          "Конотоп": (0.609, 0.826),
          "Суми": (0.685, 0.786),
          "Пирятин": (0.648, 0.722),
          "Полтава": (0.679, 0.628),
          "Кременчук": (0.620, 0.570),
          "Харків": (0.766, 0.689),
          "Ізюм": (0.910, 0.600),
          "Дніпро": (0.709, 0.495),
          "Кам'янське": (0.685, 0.517),
          "Павлоград": (0.759, 0.529),
          "Кривий Ріг": (0.622, 0.434),
          "Запоріжжя": (0.715, 0.431),
          "Нікополь": (0.678, 0.396),
          "Донецьк": (0.868, 0.458),
          "Краматорськ": (0.849, 0.548),
          "Слов'янськ": (0.929, 0.583),
          "Луганськ": (0.946, 0.541),
          "Маріуполь": (0.862, 0.356),
          "Бердянськ": (0.819, 0.322),
          "Мелітополь": (0.743, 0.307),
          "Первомайськ": (0.489, 0.443),
          "Одеса": (0.473, 0.255),
          "Миколаїв": (0.542, 0.318),
          "Херсон": (0.579, 0.277),
          "Ізмаїл": (0.420, 0.120),
          "Сімферополь": (0.671, 0.082),
          "Севастополь": (0.638, 0.039),
          "Євпаторія": (0.628, 0.112),
          "Ялта": (0.685, 0.034),
          "Керч": (0.813, 0.139),
          "Ізварине": (0.965, 0.489),
        }
        
        # Додаємо вузли, яких немає в списку доріг, але є в координатах
        for node in self.pos:
            if node not in self.graph: self.graph.add_node(node)
        # І навпаки
        for node in self.graph.nodes():
            if node not in self.pos: self.pos[node] = (0.5, 0.5)

    def create_widgets(self):
        # --- ЛІВА ПАНЕЛЬ ---
        left_panel = tk.Frame(self.root, width=350, bg="#f0f0f0", padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_panel, text="Панель керування", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=10)

        # 1. Налаштування фону
        bg_frame = tk.LabelFrame(left_panel, text="Фон (Калібрування)", bg="#f0f0f0", fg="blue")
        bg_frame.pack(fill=tk.X, pady=5)

        tk.Label(bg_frame, text="Масштаб (Zoom):", bg="#f0f0f0").pack()
        self.scale_slider = tk.Scale(bg_frame, from_=0.5, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, command=self.update_bg)
        self.scale_slider.set(1.0)
        self.scale_slider.pack(fill=tk.X)

        tk.Label(bg_frame, text="Зсув X:", bg="#f0f0f0").pack()
        self.offset_x_slider = tk.Scale(bg_frame, from_=-0.5, to=0.5, resolution=0.005, orient=tk.HORIZONTAL, command=self.update_bg)
        self.offset_x_slider.set(0.0)
        self.offset_x_slider.pack(fill=tk.X)

        tk.Label(bg_frame, text="Зсув Y:", bg="#f0f0f0").pack()
        self.offset_y_slider = tk.Scale(bg_frame, from_=-0.5, to=0.5, resolution=0.005, orient=tk.HORIZONTAL, command=self.update_bg)
        self.offset_y_slider.set(0.0)
        self.offset_y_slider.pack(fill=tk.X)

        # 2. Пошук шляху
        path_frame = tk.LabelFrame(left_panel, text="Пошук маршруту", bg="#f0f0f0")
        path_frame.pack(fill=tk.X, pady=5)

        self.start_combo = ttk.Combobox(path_frame, values=sorted(self.graph.nodes()))
        self.start_combo.set("Ужгород")
        self.start_combo.pack(fill=tk.X, pady=2)

        self.end_combo = ttk.Combobox(path_frame, values=sorted(self.graph.nodes()))
        self.end_combo.set("Луганськ")
        self.end_combo.pack(fill=tk.X, pady=2)

        tk.Button(path_frame, text="ЗНАЙТИ ШЛЯХ", command=self.find_path, bg="green", fg="white").pack(fill=tk.X, pady=5)

        self.result_text = tk.Text(left_panel, height=6, width=35, font=("Consolas", 9))
        self.result_text.pack(pady=5)

        # 3. Додавання міста/дороги
        add_frame = tk.LabelFrame(left_panel, text="Додати дорогу/місто", bg="#f0f0f0")
        add_frame.pack(fill=tk.X, pady=5)

        tk.Label(add_frame, text="Звідки (Місто 1):", bg="#f0f0f0", font=("Arial", 8)).pack(anchor="w")
        self.entry_u = tk.Entry(add_frame)
        self.entry_u.pack(fill=tk.X)

        tk.Label(add_frame, text="Куди (Місто 2):", bg="#f0f0f0", font=("Arial", 8)).pack(anchor="w")
        self.entry_v = tk.Entry(add_frame)
        self.entry_v.pack(fill=tk.X)

        tk.Label(add_frame, text="Відстань (км):", bg="#f0f0f0", font=("Arial", 8)).pack(anchor="w")
        self.entry_w = tk.Entry(add_frame)
        self.entry_w.pack(fill=tk.X)

        tk.Button(add_frame, text="Додати", command=self.add_edge_gui).pack(fill=tk.X, pady=5)

        # 4. Видалення міста
        del_frame = tk.LabelFrame(left_panel, text="Видалити місто", bg="#f0f0f0")
        del_frame.pack(fill=tk.X, pady=5)
        
        self.del_combo = ttk.Combobox(del_frame, values=sorted(self.graph.nodes()))
        self.del_combo.pack(fill=tk.X, pady=2)
        tk.Button(del_frame, text="Видалити", command=self.remove_node_gui, bg="#ffcccb").pack(fill=tk.X)

        # 5. ІНСТРУМЕНТ ДЛЯ ЗЧИТУВАННЯ КООРДИНАТ
        tk.Label(left_panel, text="Інструменти розробника:", font=("Arial", 10, "bold"), bg="#f0f0f0", fg="gray").pack(pady=(20, 0))
        tk.Button(left_panel, text="🖨 ВИВЕСТИ КООРДИНАТИ В КОНСОЛЬ", command=self.print_coordinates, bg="black", fg="white").pack(fill=tk.X, pady=5)
        tk.Label(left_panel, text="(Після перетягування натисніть цю кнопку,\nскопіюйте текст з консолі і вставте в код)", font=("Arial", 8), bg="#f0f0f0").pack()

        # --- ПРАВА ПАНЕЛЬ (Карта) ---
        self.canvas_frame = tk.Frame(self.root, bg="white")
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.figure, self.ax = plt.subplots(figsize=(10, 10))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def load_background_image(self):
        try:
            self.bg_image = mpimg.imread(self.background_image_path)
        except Exception:
            print("Фон не знайдено.")

    def update_bg(self, _=None):
        self.bg_scale = self.scale_slider.get()
        self.bg_x = self.offset_x_slider.get()
        self.bg_y = self.offset_y_slider.get()
        self.draw_graph()

    def draw_graph(self, path_edges=None):
        self.ax.clear()
        
        # Малюємо фон
        if self.bg_image is not None:
            left = 0.0 + self.bg_x
            right = (1.0 * self.bg_scale) + self.bg_x
            bottom = 0.0 + self.bg_y
            top = (1.0 * self.bg_scale) + self.bg_y
            self.ax.imshow(self.bg_image, extent=[left, right, bottom, top], aspect='auto', alpha=0.8)

        # Малюємо граф
        nx.draw_networkx_nodes(self.graph, self.pos, ax=self.ax, node_size=200, node_color='#2196F3', edgecolors='white')
        nx.draw_networkx_edges(self.graph, self.pos, ax=self.ax, edge_color='#555', alpha=0.6)
        
        # Підписи
        label_pos = {k: (v[0], v[1] + 0.025) for k, v in self.pos.items()}
        nx.draw_networkx_labels(self.graph, label_pos, ax=self.ax, font_size=8, font_weight="bold")

        # Підсвітка шляху
        if path_edges:
            nx.draw_networkx_edges(self.graph, self.pos, edgelist=path_edges, edge_color='red', width=3, ax=self.ax)
            pn = list(set([u for u,v in path_edges] + [path_edges[-1][1]]))
            nx.draw_networkx_nodes(self.graph, self.pos, nodelist=pn, node_color='red', node_size=250, ax=self.ax)

        self.ax.axis('off')
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.canvas.draw()

    def find_path(self):
        s, e = self.start_combo.get(), self.end_combo.get()
        try:
            path = nx.dijkstra_path(self.graph, s, e, weight='weight')
            dist = nx.dijkstra_path_length(self.graph, s, e, weight='weight')
            path_edges = list(zip(path, path[1:]))
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"{s} -> {e}\nВідстань: {dist} км\nМаршрут: {' -> '.join(path)}")
            self.draw_graph(path_edges)
        except:
            messagebox.showerror("Помилка", "Шлях не знайдено")

    def add_edge_gui(self):
        u, v, w_str = self.entry_u.get().strip(), self.entry_v.get().strip(), self.entry_w.get().strip()
        if u and v and w_str:
            try:
                w = int(w_str)
                self.graph.add_edge(u, v, weight=w)
                if u not in self.pos: self.pos[u] = (0.5, 0.5)
                if v not in self.pos: self.pos[v] = (0.5, 0.5)
                self.update_combos()
                self.draw_graph()
                messagebox.showinfo("Ок", f"Додано: {u}-{v} ({w} км)")
            except ValueError:
                messagebox.showerror("Помилка", "Відстань має бути числом")
        else:
            messagebox.showerror("Помилка", "Заповніть всі поля")

    def remove_node_gui(self):
        node = self.del_combo.get()
        if node in self.graph:
            self.graph.remove_node(node)
            if node in self.pos: del self.pos[node]
            self.update_combos()
            self.draw_graph()
            messagebox.showinfo("Ок", f"Місто {node} видалено")

    def update_combos(self):
        vals = sorted(self.graph.nodes())
        self.start_combo['values'] = vals
        self.end_combo['values'] = vals
        self.del_combo['values'] = vals

    def print_coordinates(self):
        """Виводить поточні координати в консоль у форматі Python-словника"""
        print("\n" + "="*30)
        print("✂️ СКОПІЮЙТЕ ЦЕЙ БЛОК І ВСТАВТЕ В self.pos:")
        print("="*30)
        print("self.pos = {")
        for node, (x, y) in self.pos.items():
            print(f'    "{node}": ({x:.3f}, {y:.3f}),')
        print("}")
        print("="*30 + "\n")
        messagebox.showinfo("Експорт", "Координати виведено в консоль (чорне вікно).")

    # Drag & Drop
    def on_press(self, event):
        if event.inaxes != self.ax: return
        for node, (x, y) in self.pos.items():
            if (x - event.xdata)**2 + (y - event.ydata)**2 < 0.0015:
                self.dragging_node = node
                break
    def on_motion(self, event):
        if self.dragging_node and event.inaxes == self.ax:
            self.pos[self.dragging_node] = (event.xdata, event.ydata)
            self.draw_graph()
    def on_release(self, event):
        self.dragging_node = None

if __name__ == "__main__":
    root = tk.Tk()
    app = RoadMapApp(root)
    root.mainloop()