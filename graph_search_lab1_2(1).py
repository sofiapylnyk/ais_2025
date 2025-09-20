
#!/usr/bin/env python3
"""
graph_search_lab1_2.py

One-file GUI application implementing:
- Random graph generator (configurable nodes, edges, directed/undirected)
- Visualization (networkx + matplotlib embedded in tkinter)
- DFS and BFS implementations with step-by-step and auto-run visualization
- Controls for start/goal, neighbor order, graph type, and reporting results

Requirements:
- Python 3.8+
- networkx
- matplotlib
- pillow (for nicer Tk icon, optional)

Run:
    python graph_search_lab1_2.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import random
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import os

# --- Utility functions ------------------------------------------------------

def ensure_connected_graph(n, m, directed=False, seed=None):
    """
    Create a connected graph with n nodes and at least n-1 edges, then add extra edges up to m.
    If directed=True, creates a DiGraph but ensures weak connectivity.
    """
    if seed is not None:
        random.seed(seed)

    # Start with a random spanning tree to guarantee connectivity
    nodes = list(range(n))
    edges = []
    remaining = nodes[:]
    random.shuffle(remaining)
    connected = [remaining.pop()]
    while remaining:
        a = random.choice(connected)
        b = remaining.pop()
        edges.append((a, b))
        connected.append(b)

    # Add random edges until we have m edges (undirected)
    attempts = 0
    while len(edges) < m and attempts < m * 10:
        a, b = random.sample(nodes, 2)
        if a == b: 
            attempts += 1
            continue
        e = (a, b)
        e_rev = (b, a)
        if directed:
            if e not in edges:
                edges.append(e)
        else:
            # keep undirected unique (store with smaller first for uniqueness)
            a1, b1 = min(a,b), max(a,b)
            if (a1, b1) not in [(min(x,y), max(x,y)) for x,y in edges]:
                edges.append((a,b))
        attempts += 1

    # If still short, allow duplicates (unlikely)
    while len(edges) < m:
        a, b = random.sample(nodes, 2)
        edges.append((a,b))

    if directed:
        G = nx.DiGraph()
    else:
        G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G

def neighbor_order_iter(neighbors, order):
    if order == 'ascending':
        return sorted(neighbors)
    if order == 'descending':
        return sorted(neighbors, reverse=True)
    if order == 'random':
        n = list(neighbors)
        random.shuffle(n)
        return n
    # 'given' default
    return list(neighbors)

# --- Graph search algorithms as generators for step-by-step visualization ---

def dfs_generator(G, start, goal, neighbor_order='given'):
    visited = set()
    stack = [(start, iter(neighbor_order_iter(G.neighbors(start), neighbor_order)))]
    parent = {start: None}
    opened_count = 0
    # yield initial state
    yield {'action': 'init', 'current': start, 'visited': set(), 'stack': [start], 'parent': parent.copy(), 'opened': opened_count}
    while stack:
        node, children_iter = stack[-1]
        if node not in visited:
            visited.add(node)
            opened_count += 1
            yield {'action': 'visit', 'current': node, 'visited': visited.copy(), 'stack': [n for n,_ in stack], 'parent': parent.copy(), 'opened': opened_count}
            if node == goal:
                # Build path
                path = []
                cur = node
                while cur is not None:
                    path.append(cur)
                    cur = parent.get(cur)
                path.reverse()
                yield {'action': 'found', 'path': path, 'visited': visited.copy(), 'opened': opened_count, 'parent': parent.copy()}
                return
        try:
            nb = next(children_iter)
            if nb not in visited:
                parent[nb] = node
                stack.append((nb, iter(neighbor_order_iter(G.neighbors(nb), neighbor_order))))
                yield {'action': 'push', 'current': nb, 'visited': visited.copy(), 'stack': [n for n,_ in stack], 'parent': parent.copy(), 'opened': opened_count}
            else:
                # skipping visited neighbor
                yield {'action': 'skip', 'current': nb, 'visited': visited.copy(), 'stack': [n for n,_ in stack], 'parent': parent.copy(), 'opened': opened_count}
        except StopIteration:
            # done with this node
            stack.pop()
            yield {'action': 'pop', 'current': node, 'visited': visited.copy(), 'stack': [n for n,_ in stack], 'parent': parent.copy(), 'opened': opened_count}
    # not found
    yield {'action': 'not_found', 'visited': visited.copy(), 'opened': opened_count, 'parent': parent.copy()}

from collections import deque
def bfs_generator(G, start, goal, neighbor_order='given'):
    visited = set([start])
    parent = {start: None}
    queue = deque([start])
    opened_count = 1
    yield {'action': 'init', 'current': start, 'visited': visited.copy(), 'queue': list(queue), 'parent': parent.copy(), 'opened': opened_count}
    while queue:
        node = queue.popleft()
        yield {'action': 'visit', 'current': node, 'visited': visited.copy(), 'queue': list(queue), 'parent': parent.copy(), 'opened': opened_count}
        if node == goal:
            path = []
            cur = node
            while cur is not None:
                path.append(cur)
                cur = parent.get(cur)
            path.reverse()
            yield {'action': 'found', 'path': path, 'visited': visited.copy(), 'opened': opened_count, 'parent': parent.copy()}
            return
        for nb in neighbor_order_iter(G.neighbors(node), neighbor_order):
            if nb not in visited:
                visited.add(nb)
                parent[nb] = node
                queue.append(nb)
                opened_count += 1
                yield {'action': 'enqueue', 'current': nb, 'visited': visited.copy(), 'queue': list(queue), 'parent': parent.copy(), 'opened': opened_count}
            else:
                yield {'action': 'skip', 'current': nb, 'visited': visited.copy(), 'queue': list(queue), 'parent': parent.copy(), 'opened': opened_count}
    yield {'action': 'not_found', 'visited': visited.copy(), 'opened': opened_count, 'parent': parent.copy()}

# --- GUI Application --------------------------------------------------------

class GraphSearchApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("Lab 1 & 2 — Graph Blind Search (DFS & BFS)")
        self.pack(fill='both', expand=True)
        self.G = None
        self.pos = None
        self.current_generator = None
        self.auto_running = False
        self.step_delay = 500  # ms
        
        # default params
        self.node_count = tk.IntVar(value=30)
        self.edge_count = tk.IntVar(value=40)
        self.directed = tk.BooleanVar(value=False)
        self.neighbor_order = tk.StringVar(value='given')
        self.search_algo = tk.StringVar(value='DFS')
        self.start_node = tk.IntVar(value=0)
        self.goal_node = tk.IntVar(value=1)
        self.speed_ms = tk.IntVar(value=500)
        
        self._build_ui()
        self._create_plot()
        self.generate_graph()

    def _build_ui(self):
        # Controls on left
        ctrl = ttk.Frame(self)
        ctrl.pack(side='left', fill='y', padx=8, pady=8)
        row = 0

        ttk.Label(ctrl, text="Graph parameters", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        ttk.Label(ctrl, text="Nodes:").grid(row=row, column=0, sticky='e')
        ttk.Spinbox(ctrl, from_=10, to=200, textvariable=self.node_count, width=8).grid(row=row, column=1, sticky='w'); row+=1
        ttk.Label(ctrl, text="Edges:").grid(row=row, column=0, sticky='e')
        ttk.Spinbox(ctrl, from_=9, to=1000, textvariable=self.edge_count, width=8).grid(row=row, column=1, sticky='w'); row+=1
        ttk.Checkbutton(ctrl, text="Directed (DiGraph)", variable=self.directed).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        ttk.Separator(ctrl, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=4); row+=1

        ttk.Label(ctrl, text="Search & neighbor order", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        ttk.Radiobutton(ctrl, text='DFS', variable=self.search_algo, value='DFS').grid(row=row, column=0, sticky='w')
        ttk.Radiobutton(ctrl, text='BFS', variable=self.search_algo, value='BFS').grid(row=row, column=1, sticky='w'); row+=1

        ttk.Label(ctrl, text="Neighbor order:").grid(row=row, column=0, sticky='w')
        orders = ['given', 'ascending', 'descending', 'random']
        ttk.OptionMenu(ctrl, self.neighbor_order, self.neighbor_order.get(), *orders).grid(row=row, column=1, sticky='w'); row+=1

        ttk.Separator(ctrl, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=4); row+=1

        ttk.Label(ctrl, text="Start / Goal", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        self.start_combo = ttk.Combobox(ctrl, values=[], textvariable=self.start_node, width=6)
        self.goal_combo = ttk.Combobox(ctrl, values=[], textvariable=self.goal_node, width=6)
        ttk.Label(ctrl, text="Start:").grid(row=row, column=0, sticky='e'); self.start_combo.grid(row=row, column=1, sticky='w'); row+=1
        ttk.Label(ctrl, text="Goal:").grid(row=row, column=0, sticky='e'); self.goal_combo.grid(row=row, column=1, sticky='w'); row+=1

        ttk.Separator(ctrl, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=4); row+=1
        ttk.Label(ctrl, text="Execution", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        ttk.Label(ctrl, text="Step delay (ms):").grid(row=row, column=0, sticky='e')
        ttk.Spinbox(ctrl, from_=50, to=2000, textvariable=self.speed_ms, width=8).grid(row=row, column=1, sticky='w'); row+=1

        ttk.Button(ctrl, text="Generate Graph", command=self.generate_graph).grid(row=row, column=0, columnspan=2, sticky='ew'); row+=1
        ttk.Button(ctrl, text="Run (Auto)", command=self.run_auto).grid(row=row, column=0, columnspan=2, sticky='ew'); row+=1
        ttk.Button(ctrl, text="Step", command=self.run_step).grid(row=row, column=0, sticky='ew')
        ttk.Button(ctrl, text="Reset", command=self.reset_run).grid(row=row, column=1, sticky='ew'); row+=1

        ttk.Separator(ctrl, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=4); row+=1

        ttk.Label(ctrl, text="Results", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky='w'); row+=1
        self.results_text = tk.Text(ctrl, width=30, height=12, state='disabled', wrap='word')
        self.results_text.grid(row=row, column=0, columnspan=2); row+=1

        # Footer
        ttk.Label(ctrl, text="Produced for Lab 1 & 2 — DFS & BFS", font=('Segoe UI', 8)).grid(row=row, column=0, columnspan=2, sticky='w', pady=(6,0))

    def _create_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(6,6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side='right', fill='both', expand=True)
        plt.tight_layout()

    def generate_graph(self):
        n = max(10, int(self.node_count.get()))
        m = max(n-1, int(self.edge_count.get()))
        directed = bool(self.directed.get())
        self.G = ensure_connected_graph(n, m, directed=directed)
        # position nodes deterministically (fixed) for reproducibility
        self.pos = nx.spring_layout(self.G, seed=42)
        # update comboboxes
        nodes = sorted(self.G.nodes())
        vals = [str(x) for x in nodes]
        self.start_combo['values'] = vals
        self.goal_combo['values'] = vals
        if str(self.start_node.get()) not in vals:
            self.start_node.set(nodes[0])
        if str(self.goal_node.get()) not in vals:
            self.goal_node.set(nodes[min(1, len(nodes)-1)])
        self.reset_run()
        self.draw_graph()

    def draw_graph(self, highlight_nodes=None, highlight_edges=None, visited=None, frontier=None, path=None):
        self.ax.clear()
        if self.G is None:
            return
        default_node_color = '#dddddd'
        node_colors = []
        node_sizes = []
        for n in self.G.nodes():
            if path and n in path:
                node_colors.append('#7be57b')  # green for path
                node_sizes.append(280)
            elif visited and n in visited:
                node_colors.append('#bbbbbb')  # visited - gray
                node_sizes.append(200)
            elif frontier and n in frontier:
                node_colors.append('#fff79a')  # frontier - yellow
                node_sizes.append(220)
            else:
                node_colors.append(default_node_color)
                node_sizes.append(160)
        edge_colors = []
        for e in self.G.edges():
            if highlight_edges and e in highlight_edges:
                edge_colors.append('#ff6666')
            else:
                edge_colors.append('#999999')
        nx.draw_networkx_nodes(self.G, pos=self.pos, ax=self.ax, node_color=node_colors, node_size=node_sizes)
        nx.draw_networkx_edges(self.G, pos=self.pos, ax=self.ax, edge_color=edge_colors)
        labels = {n: str(n) for n in self.G.nodes()}
        nx.draw_networkx_labels(self.G, pos=self.pos, labels=labels, font_size=8)
        # highlight start and goal specially
        try:
            s = int(self.start_node.get())
            g = int(self.goal_node.get())
            if s in self.G.nodes():
                nx.draw_networkx_nodes(self.G, pos=self.pos, nodelist=[s], node_color='#ff9999', node_size=380, ax=self.ax)  # red start
            if g in self.G.nodes():
                nx.draw_networkx_nodes(self.G, pos=self.pos, nodelist=[g], node_color='#9999ff', node_size=380, ax=self.ax)  # blue goal
        except Exception:
            pass
        self.ax.set_title(f"Graph: nodes={self.G.number_of_nodes()}, edges={self.G.number_of_edges()}, directed={self.directed.get()}")
        self.ax.axis('off')
        self.canvas.draw_idle()

    def reset_run(self):
        self.current_generator = None
        self.auto_running = False
        self.append_result("Reset run state.\n")
        self.draw_graph()

    def append_result(self, text):
        self.results_text.configure(state='normal')
        self.results_text.insert('end', text + '\n')
        self.results_text.see('end')
        self.results_text.configure(state='disabled')

    def run_step(self):
        if self.G is None:
            messagebox.showwarning("No graph", "Please generate a graph first.")
            return
        if self.current_generator is None:
            # create generator based on selection
            start = int(self.start_node.get())
            goal = int(self.goal_node.get())
            order = self.neighbor_order.get()
            if self.search_algo.get() == 'DFS':
                self.current_generator = dfs_generator(self.G, start, goal, neighbor_order=order)
            else:
                self.current_generator = bfs_generator(self.G, start, goal, neighbor_order=order)
        try:
            state = next(self.current_generator)
            self._handle_state(state)
        except StopIteration:
            self.append_result("Generator finished.")
            self.current_generator = None

    def _handle_state(self, state):
        act = state.get('action')
        if act == 'init':
            self.append_result(f"Init: start={state.get('current')}")
            self.draw_graph(visited=state.get('visited'))
        elif act == 'visit':
            cur = state.get('current')
            self.append_result(f"Visit: {cur} (opened so far: {state.get('opened')})")
            visited = state.get('visited')
            self.draw_graph(visited=visited, frontier=state.get('stack') if 'stack' in state else state.get('queue'))
        elif act in ('push','enqueue'):
            cur = state.get('current')
            self.append_result(f"{act.title()}: {cur} (opened: {state.get('opened')})")
            visited = state.get('visited')
            frontier = state.get('stack') if 'stack' in state else state.get('queue')
            self.draw_graph(visited=visited, frontier=frontier)
        elif act == 'skip':
            self.append_result(f"Skip neighbor: {state.get('current')}")
        elif act == 'pop':
            self.append_result(f"Backtrack (pop): {state.get('current')}")
            self.draw_graph(visited=state.get('visited'), frontier=state.get('stack'))
        elif act == 'found':
            path = state.get('path')
            self.append_result(f"Found! Path length: {len(path)}; opened: {state.get('opened')}")
            self.append_result("Path: " + " -> ".join(map(str, path)))
            # highlight path edges
            edges = []
            for i in range(len(path)-1):
                a, b = path[i], path[i+1]
                if self.directed.get():
                    edges.append((a,b))
                else:
                    # edges in graph might be (min,max) or original orientation, networkx draws undirected edges as tuple (a,b)
                    edges.append((a,b))
                # also try reverse for highlighting in undirected
                if not self.directed.get():
                    edges.append((b,a))
            self.draw_graph(path=path, highlight_edges=edges, visited=state.get('visited'))
            self.current_generator = None
        elif act == 'not_found':
            self.append_result(f"Not found. Opened: {state.get('opened')}")
            self.draw_graph(visited=state.get('visited'))
            self.current_generator = None
        else:
            # generic handling
            self.append_result(str(state))
            self.draw_graph(visited=state.get('visited'))
    
    def run_auto(self):
        if self.G is None:
            messagebox.showwarning("No graph", "Please generate a graph first.")
            return
        # initialize generator if needed
        if self.current_generator is None:
            start = int(self.start_node.get())
            goal = int(self.goal_node.get())
            order = self.neighbor_order.get()
            if self.search_algo.get() == 'DFS':
                self.current_generator = dfs_generator(self.G, start, goal, neighbor_order=order)
            else:
                self.current_generator = bfs_generator(self.G, start, goal, neighbor_order=order)
        # toggle auto_running
        if self.auto_running:
            self.auto_running = False
            self.append_result("Auto run stopped by user.")
            return
        self.auto_running = True
        self.step_delay = max(10, int(self.speed_ms.get()))
        self.append_result("Auto run started.")
        self._auto_step()

    def _auto_step(self):
        if not self.auto_running or self.current_generator is None:
            self.auto_running = False
            return
        try:
            state = next(self.current_generator)
            self._handle_state(state)
        except StopIteration:
            self.append_result("Auto generator finished.")
            self.current_generator = None
            self.auto_running = False
            return
        # schedule next automatic step
        self.master.after(self.step_delay, self._auto_step)


def main():
    root = tk.Tk()
    app = GraphSearchApp(root)
    root.geometry('1100x720')
    root.mainloop()

if __name__ == '__main__':
    main()
