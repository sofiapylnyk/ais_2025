import tkinter as tk
from tkinter import messagebox, simpledialog
from collections import deque
import random
import time
import sys

# --- Налаштування GUI та Констант ---
CELL_SIZE = 30
WALL = -1
PASSAGE = 0
START = 1
GOAL = 2
PATH = 3
VISITED = 4
FONT_STYLE = ('Arial', 10, 'bold')
VISUALIZATION_DELAY_MS = 10  # Затримка в мілісекундах для покрокової візуалізації

# Збільшення ліміту рекурсії для можливого візуального оновлення
sys.setrecursionlimit(2000) 

class WaveSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("🌊 Хвильовий Пошук у Лабіринті")
        
        # Параметри лабіринту за замовчуванням
        self.rows = 15
        self.cols = 15
        self.wall_density = 0.3
        self.grid = []
        self.start_node = (0, 0)
        self.goal_node = (self.rows - 1, self.cols - 1)
        self.path_result = []
        self.cycles = 0
        self.search_running = False
        
        # Створення головних фреймів
        self.controls_frame = tk.Frame(master)
        self.controls_frame.pack(side=tk.LEFT, padx=10, pady=10, anchor='n')
        
        self.canvas_frame = tk.Frame(master)
        self.canvas_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.results_frame = tk.Frame(master)
        self.results_frame.pack(side=tk.RIGHT, padx=10, pady=10, anchor='n')

        self.create_controls()
        self.create_canvas()
        self.create_results_window()
        
        self.generate_labyrinth()

    def create_controls(self):
        # --- Налаштування Розміру та Щільності ---
        tk.Label(self.controls_frame, text="📐 Параметри Лабіринту", font=FONT_STYLE).pack(pady=(5, 0))
        
        frame_size = tk.Frame(self.controls_frame)
        frame_size.pack()
        tk.Label(frame_size, text="Рядків:").pack(side=tk.LEFT)
        self.row_entry = tk.Entry(frame_size, width=5)
        self.row_entry.insert(0, str(self.rows))
        self.row_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(frame_size, text="Стовпців:").pack(side=tk.LEFT)
        self.col_entry = tk.Entry(frame_size, width=5)
        self.col_entry.insert(0, str(self.cols))
        self.col_entry.pack(side=tk.LEFT)
        
        tk.Label(self.controls_frame, text="Щільність Стін (0.1-0.5):").pack(pady=(5, 0))
        self.density_entry = tk.Entry(self.controls_frame, width=5)
        self.density_entry.insert(0, str(self.wall_density))
        self.density_entry.pack(pady=5)
        
        tk.Button(self.controls_frame, text="🛠️ Згенерувати Лабіринт", command=self.generate_labyrinth).pack(pady=10)

        # --- Вибір Оператора Переходу ---
        tk.Label(self.controls_frame, text="➡️ Оператор Переходу:", font=FONT_STYLE).pack(pady=(10, 0))
        self.operator_var = tk.StringVar(self.master)
        self.operator_var.set("Cardinal (ВВВЛ)")
        operators = ["Cardinal (ВВВЛ)", "Diagonal (Діагоналі)", "Combined (Комбінований)"]
        self.operator_menu = tk.OptionMenu(self.controls_frame, self.operator_var, *operators)
        self.operator_menu.pack(pady=5)
        
        # --- Налаштування Початкової/Цільової Вершини ---
        tk.Label(self.controls_frame, text="🎯 Точки (Ряд, Стовпець):", font=FONT_STYLE).pack(pady=(10, 0))
        frame_start = tk.Frame(self.controls_frame)
        frame_start.pack()
        tk.Label(frame_start, text="S:").pack(side=tk.LEFT)
        self.start_row_entry = tk.Entry(frame_start, width=4)
        self.start_row_entry.pack(side=tk.LEFT)
        self.start_col_entry = tk.Entry(frame_start, width=4)
        self.start_col_entry.pack(side=tk.LEFT)
        
        frame_goal = tk.Frame(self.controls_frame)
        frame_goal.pack()
        tk.Label(frame_goal, text="G:").pack(side=tk.LEFT)
        self.goal_row_entry = tk.Entry(frame_goal, width=4)
        self.goal_row_entry.pack(side=tk.LEFT)
        self.goal_col_entry = tk.Entry(frame_goal, width=4)
        self.goal_col_entry.pack(side=tk.LEFT)
        
        tk.Button(self.controls_frame, text="Оновити Точки", command=self.update_start_goal).pack(pady=5)
        
        # --- Кнопки Пошуку та Візуалізації ---
        tk.Button(self.controls_frame, text="🔎 Знайти Шлях", command=self.start_search, bg='lightblue').pack(pady=20)
        tk.Button(self.controls_frame, text="🔠 Показати Матрицю Суміжності", command=self.show_adjacency_matrix).pack(pady=5)


    def create_canvas(self):
        # Створення полотна для візуалізації лабіринту
        self.canvas_width = self.cols * CELL_SIZE
        self.canvas_height = self.rows * CELL_SIZE
        self.canvas = tk.Canvas(self.canvas_frame, width=self.canvas_width, height=self.canvas_height, bg='white')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def create_results_window(self):
        # --- Вікно Результатів ---
        tk.Label(self.results_frame, text="📊 Результати Пошуку", font=FONT_STYLE).pack(pady=(5, 0))
        self.results_text = tk.Text(self.results_frame, height=15, width=40, state=tk.DISABLED, wrap=tk.WORD)
        self.results_text.pack(pady=10)
        
        # Налаштування затримки
        tk.Label(self.results_frame, text="Затримка візуалізації (мс):", font=('Arial', 9)).pack(pady=(10, 0))
        self.delay_scale = tk.Scale(self.results_frame, from_=0, to=500, orient=tk.HORIZONTAL, length=200)
        self.delay_scale.set(VISUALIZATION_DELAY_MS)
        self.delay_scale.pack()

    def on_canvas_click(self, event):
        # Обробка кліків для зміни стін
        if self.search_running:
             messagebox.showinfo("Увага", "Пошук триває. Зачекайте.")
             return
             
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if (row, col) != self.start_node and (row, col) != self.goal_node:
                # Зміна стіна <-> прохід
                if self.grid[row][col] == WALL:
                    self.grid[row][col] = PASSAGE
                else:
                    self.grid[row][col] = WALL
                self.draw_labyrinth()
                self.path_result = [] 
                self.update_results()

    def update_start_goal(self):
        try:
            r_start = int(self.start_row_entry.get())
            c_start = int(self.start_col_entry.get())
            r_goal = int(self.goal_row_entry.get())
            c_goal = int(self.goal_col_entry.get())
            
            if not (0 <= r_start < self.rows and 0 <= c_start < self.cols and
                    0 <= r_goal < self.rows and 0 <= c_goal < self.cols):
                raise ValueError("Координати поза межами лабіринту.")
            
            # Перевірка, щоб старт/ціль не були стінами
            if self.grid[r_start][c_start] == WALL or self.grid[r_goal][c_goal] == WALL:
                messagebox.showerror("Помилка", "Стартова або цільова точка не може бути стіною (-1).")
                return

            self.start_node = (r_start, c_start)
            self.goal_node = (r_goal, c_goal)
            
            self.draw_labyrinth()
            self.path_result = []
            self.update_results()

        except ValueError as e:
            messagebox.showerror("Помилка Вводу", f"Неправильні координати: {e}")

    def generate_labyrinth(self):
        try:
            self.rows = int(self.row_entry.get())
            self.cols = int(self.col_entry.get())
            self.wall_density = float(self.density_entry.get())
            
            # Обмеження графу порядку 10-20, розміром 20-30
            if not (5 <= self.rows <= 30 and 5 <= self.cols <= 30 and 0.1 <= self.wall_density <= 0.5):
                raise ValueError("Розмір має бути 5-30, щільність 0.1-0.5.")
                
            self.canvas_width = self.cols * CELL_SIZE
            self.canvas_height = self.rows * CELL_SIZE
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)

            # Створення матриці: 0 - прохід, -1 - стіна
            self.grid = [[random.choices([PASSAGE, WALL], weights=[1 - self.wall_density, self.wall_density])[0]
                          for _ in range(self.cols)] for _ in range(self.rows)]
            
            # Оновлення початкової та цільової точок
            self.start_node = (0, 0)
            self.goal_node = (self.rows - 1, self.cols - 1)
            
            # Гарантуємо, що старт і ціль - проходи
            self.grid[self.start_node[0]][self.start_node[1]] = PASSAGE
            self.grid[self.goal_node[0]][self.goal_node[1]] = PASSAGE
            
            # Оновлення полів вводу
            self.start_row_entry.delete(0, tk.END)
            self.start_row_entry.insert(0, str(self.start_node[0]))
            self.start_col_entry.delete(0, tk.END)
            self.start_col_entry.insert(0, str(self.start_node[1]))
            self.goal_row_entry.delete(0, tk.END)
            self.goal_row_entry.insert(0, str(self.goal_node[0]))
            self.goal_col_entry.delete(0, tk.END)
            self.goal_col_entry.insert(0, str(self.goal_node[1]))

            self.draw_labyrinth()
            self.path_result = []
            self.update_results()

        except ValueError as e:
            messagebox.showerror("Помилка Вводу", f"Неправильні параметри: {e}")

    def draw_labyrinth(self, path=None, visited_nodes=None):
        self.canvas.delete("all")
        
        # Визначення кольорів
        color_map = {
            WALL: 'gray',
            PASSAGE: 'white',
            START: 'green',
            GOAL: 'red',
            PATH: 'blue',
            VISITED: 'lightblue'
        }
        
        for r in range(self.rows):
            for c in range(self.cols):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                
                cell_type = self.grid[r][c]
                fill_color = color_map.get(cell_type, 'white')
                
                # Заповнення відвіданих
                if visited_nodes and (r, c) in visited_nodes and (r, c) != self.start_node and (r, c) != self.goal_node:
                    fill_color = color_map[VISITED]
                    
                # Заповнення шляху
                if path and (r, c) in path and (r, c) != self.start_node and (r, c) != self.goal_node:
                    fill_color = color_map[PATH]

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline='black')
                
        # 2. Малювання Старт/Ціль поверх усього
        r_start, c_start = self.start_node
        r_goal, c_goal = self.goal_node
        
        for r, c, tag in [(r_start, c_start, "S"), (r_goal, c_goal, "G")]:
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
            color = color_map[START] if tag == "S" else color_map[GOAL]
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='black')
            self.canvas.create_text(x1 + CELL_SIZE/2, y1 + CELL_SIZE/2, text=tag, fill='white', font=FONT_STYLE)

        self.master.update_idletasks()
        self.master.update()


    def get_neighbors(self, r, c, operator):
        # Визначення напрямків переходу (оператор переходу)
        operator_map = {
            "Cardinal (ВВВЛ)": [(0, 1), (0, -1), (1, 0), (-1, 0)],
            "Diagonal (Діагоналі)": [(1, 1), (1, -1), (-1, 1), (-1, -1)],
            "Combined (Комбінований)": [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        }
        
        directions = operator_map.get(operator, operator_map["Cardinal (ВВВЛ)"])

        neighbors = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self.grid[nr][nc] != WALL:
                    neighbors.append((nr, nc))
        return neighbors

    def wave_search(self, start_node, goal_node, operator):
        """Реалізація одно-направленого хвильового пошуку (BFS) з покроковою візуалізацією."""
        
        if self.grid[start_node[0]][start_node[1]] == WALL or self.grid[goal_node[0]][goal_node[1]] == WALL:
            return None, 0
        
        queue = deque([start_node])
        visited = {start_node}
        parent = {start_node: None}
        cycles = 0
        delay = self.delay_scale.get()

        self.search_running = True
        
        while queue:
            current_node = queue.popleft()
            cycles += 1
            
            # 💡 Покрокова Візуалізація на кожному циклі
            self.draw_labyrinth(visited_nodes=visited)
            if delay > 0:
                self.master.after(delay)
                self.master.update()

            if current_node == goal_node:
                # Шлях знайдено
                path = []
                while current_node is not None:
                    path.append(current_node)
                    current_node = parent[current_node]
                self.search_running = False
                return path[::-1], cycles

            # Розкриття вершини (сусіди)
            for neighbor in self.get_neighbors(current_node[0], current_node[1], operator):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current_node
                    queue.append(neighbor)
        
        self.search_running = False
        return None, cycles

    def start_search(self):
        if self.search_running:
            messagebox.showinfo("Увага", "Пошук вже триває.")
            return

        self.draw_labyrinth()
        self.path_result = []
        self.cycles = 0
        self.update_start_goal()

        operator = self.operator_var.get()
        
        start_time = time.time()
        path, cycles = self.wave_search(self.start_node, self.goal_node, operator)
        end_time = time.time()
        search_time = end_time - start_time
        
        self.cycles = cycles
        self.path_result = path
        
        if path:
            self.draw_labyrinth(path=path)
            message = "✅ Шлях знайдено!"
        else:
            self.draw_labyrinth()
            message = "❌ Шлях не знайдено."
        
        self.update_results(message, search_time, len(path) if path else 0, operator)

    def update_results(self, message="Очікування запуску", time=0.0, path_len=0, operator="N/A"):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        output = f"--- РЕЗУЛЬТАТИ ПОШУКУ ---\n\n"
        output += f"Статус: {message}\n"
        output += f"Оператор: {operator}\n"
        output += f"Час пошуку: {time:.6f} сек\n"
        output += f"Цикли (Розкриття Вершин): {self.cycles}\n"
        output += f"Довжина шляху: {path_len}\n"
        output += f"Розмір Лабіринту: {self.rows}x{self.cols}\n"
        
        if self.path_result:
            output += "\nКоординати Знайденого Шляху (частина):\n"
            path_str = " -> ".join([f"({r},{c})" for r, c in self.path_result[:10]])
            if len(self.path_result) > 10:
                 path_str += " -> ..."
            output += path_str
            
        self.results_text.insert(tk.END, output)
        self.results_text.config(state=tk.DISABLED)

    def show_adjacency_matrix(self):
        # 1. Створення мапи (Координати -> Індекс вершини) для прохідних комірок
        node_map = {}
        idx = 0
        passage_nodes = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != WALL:
                    node_map[(r, c)] = idx
                    passage_nodes.append((r, c))
                    idx += 1
        
        N = len(passage_nodes) # Порядок графу (кількість прохідних вершин)
        
        if N == 0:
             messagebox.showinfo("Помилка", "У лабіринті немає прохідних вершин.")
             return
             
        # 2. Створення N x N матриці суміжності
        adjacency_matrix = [[0] * N for _ in range(N)]
        
        # Використовуємо комбінований оператор для визначення суміжності
        # (всі можливі переходи, які впливають на структуру графу)
        operator_type = "Combined (Комбінований)" 
        
        for r, c in passage_nodes:
            current_idx = node_map[(r, c)]
            # Отримання сусідів, які є прохідними
            neighbors = self.get_neighbors(r, c, operator_type)
            
            for nr, nc in neighbors:
                neighbor_idx = node_map[(nr, nc)]
                # Незважений граф: 1, якщо суміжні
                adjacency_matrix[current_idx][neighbor_idx] = 1 

        # 3. Виведення у новому вікні
        matrix_window = tk.Toplevel(self.master)
        matrix_window.title(f"Матриця Суміжності (Порядок N={N})")
        
        header_text = f"Матриця суміжності N={N} (Прохідні вершини: {self.rows*self.cols - N} стін)\n\n"
        header_text += "Вершини (Індекс: (Ряд, Стовпець)):\n"
        
        # Виведення мапи індексів
        map_str = ""
        for coord, index in node_map.items():
            map_str += f"{index}: {coord} | "
            if (index + 1) % 5 == 0: map_str += "\n"
        
        matrix_text = tk.Text(matrix_window, height=30, width=80, wrap=tk.NONE)
        matrix_text.pack(padx=10, pady=10)
        matrix_text.insert(tk.END, header_text)
        matrix_text.insert(tk.END, map_str + "\n\n")

        # Виведення самої матриці (обмеження для великих матриць)
        matrix_str = ""
        max_size = min(N, 50)
        
        for r in range(max_size):
            row_str = " ".join([f"{cell}" for cell in adjacency_matrix[r][:max_size]])
            matrix_str += row_str
            if max_size < N:
                 matrix_str += " ..."
            matrix_str += "\n"
        
        if max_size < N:
            matrix_str += "...\n"
        
        matrix_text.insert(tk.END, "--- Матриця A[N][N] ---\n")
        matrix_text.insert(tk.END, matrix_str)
        matrix_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = WaveSearchApp(root)
    root.mainloop()