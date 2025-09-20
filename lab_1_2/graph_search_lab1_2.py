#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import networkx as nx
import random, json, csv, copy, math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import time

def ensure_connected_graph(n, m, directed=False, seed=None):
    if seed is not None:
        random.seed(seed)
    nodes = list(range(n))
    edges = []
    remaining = nodes[:]
    random.shuffle(remaining)
    connected = [remaining.pop()]
    while remaining:
        a = random.choice(connected); b = remaining.pop(); edges.append((a,b)); connected.append(b)
    attempts = 0
    while len(edges) < m and attempts < m*10:
        a,b = random.sample(nodes,2)
        if a==b: attempts+=1; continue
        if not directed:
            a1,b1 = min(a,b), max(a,b)
            if (a1,b1) not in [(min(x,y),max(x,y)) for x,y in edges]:
                edges.append((a,b))
        else:
            if (a,b) not in edges:
                if (b,a) in edges:
                    attempts+=1
                    continue
                edges.append((a,b))
        attempts+=1
    while len(edges) < m:
        a,b = random.sample(nodes,2); edges.append((a,b))
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    if directed:
        G.add_edges_from(edges)
    else:
        for a,b in edges:
            G.add_edge(a,b, directed=False); G.add_edge(b,a, directed=False)
    return G

def neighbor_order_iter(G, node, order):
    neigh = list(G.successors(node))
    if order=='ascending': return sorted(neigh)
    if order=='descending': return sorted(neigh, reverse=True)
    if order=='random': 
        n=list(neigh); random.shuffle(n); return n
    return neigh

def dfs_generator(G, start, goal, neighbor_order='given'):
    visited=set(); stack=[(start, iter(neighbor_order_iter(G,start,neighbor_order)))]; parent={start:None}; opened=0
    yield {'action':'init','current':start,'visited':set(),'stack':[start],'parent':parent.copy(),'opened':opened}
    while stack:
        node,children=stack[-1]
        if node not in visited:
            visited.add(node); opened+=1
            yield {'action':'visit','current':node,'visited':visited.copy(),'stack':[n for n,_ in stack],'parent':parent.copy(),'opened':opened}
            if node==goal:
                path=[]; cur=node
                while cur is not None: path.append(cur); cur=parent.get(cur)
                path.reverse(); yield {'action':'found','path':path,'visited':visited.copy(),'opened':opened,'parent':parent.copy()}; return
        try:
            nb=next(children)
            if nb not in visited:
                parent[nb]=node; stack.append((nb, iter(neighbor_order_iter(G,nb,neighbor_order))))
                yield {'action':'push','current':nb,'visited':visited.copy(),'stack':[n for n,_ in stack],'parent':parent.copy(),'opened':opened}
            else:
                yield {'action':'skip','current':nb,'visited':visited.copy(),'stack':[n for n,_ in stack],'parent':parent.copy(),'opened':opened}
        except StopIteration:
            stack.pop(); yield {'action':'pop','current':node,'visited':visited.copy(),'stack':[n for n,_ in stack],'parent':parent.copy(),'opened':opened}
    yield {'action':'not_found','visited':visited.copy(),'opened':opened,'parent':parent.copy()}

def bfs_generator(G, start, goal, neighbor_order='given'):
    visited=set([start]); parent={start:None}; queue=deque([start]); opened=1
    yield {'action':'init','current':start,'visited':visited.copy(),'queue':list(queue),'parent':parent.copy(),'opened':opened}
    while queue:
        node=queue.popleft()
        yield {'action':'visit','current':node,'visited':visited.copy(),'queue':list(queue),'parent':parent.copy(),'opened':opened}
        if node==goal:
            path=[]; cur=node
            while cur is not None: path.append(cur); cur=parent.get(cur)
            path.reverse(); yield {'action':'found','path':path,'visited':visited.copy(),'opened':opened,'parent':parent.copy()}; return
        for nb in neighbor_order_iter(G,node,neighbor_order):
            if nb not in visited:
                visited.add(nb); parent[nb]=node; queue.append(nb); opened+=1
                yield {'action':'enqueue','current':nb,'visited':visited.copy(),'queue':list(queue),'parent':parent.copy(),'opened':opened}
            else:
                yield {'action':'skip','current':nb,'visited':visited.copy(),'queue':list(queue),'parent':parent.copy(),'opened':opened}
    yield {'action':'not_found','visited':visited.copy(),'opened':opened,'parent':parent.copy()}

class GraphSearchApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master); self.master=master; self.master.title("Graph Editor + DFS/BFS"); self.pack(fill='both',expand=True)
        self.G=None; self.pos={}; self.current_generator=None; self.auto_running=False; self.step_delay=300
        self.edit_mode=tk.BooleanVar(value=False); self.selected_source_for_edge=None; self.dragging_node=None; self.drag_offset=(0,0)
        self.node_hit_threshold=0.04; self.edge_hit_threshold=0.02
        self.undo_stack=[]; self.redo_stack=[]
        self.node_count=tk.IntVar(value=30); self.edge_count=tk.IntVar(value=40)
        self.initial_directed=tk.BooleanVar(value=False); self.neighbor_order=tk.StringVar(value='given')
        self.search_algo=tk.StringVar(value='DFS'); self.start_node=tk.IntVar(value=0); self.goal_node=tk.IntVar(value=1); self.speed_ms=tk.IntVar(value=500)
        self._start_time = None
        self._build_ui(); self._create_plot(); self.generate_graph()

    def _build_ui(self):
        ctrl=ttk.Frame(self); ctrl.pack(side='left',fill='y',padx=10,pady=10)
        btn_opts={'width':20,'padding':6}
        ttk.Label(ctrl,text="Graph parameters",font=('Segoe UI',11,'bold')).pack(anchor='w')
        frm=ttk.Frame(ctrl); frm.pack(fill='x',pady=4)
        ttk.Label(frm,text="Nodes:").grid(row=0,column=0); ttk.Spinbox(frm,from_=5,to=300,textvariable=self.node_count,width=6).grid(row=0,column=1)
        ttk.Label(frm,text="Edges:").grid(row=1,column=0); ttk.Spinbox(frm,from_=4,to=2000,textvariable=self.edge_count,width=6).grid(row=1,column=1)
        ttk.Checkbutton(ctrl,text="Initial Directed (new edges)",variable=self.initial_directed).pack(anchor='w',pady=2)
        ttk.Separator(ctrl,orient='horizontal').pack(fill='x',pady=6)
        ttk.Label(ctrl,text="Search & Order",font=('Segoe UI',11,'bold')).pack(anchor='w')
        ttk.Radiobutton(ctrl,text='DFS',variable=self.search_algo,value='DFS').pack(anchor='w')
        ttk.Radiobutton(ctrl,text='BFS',variable=self.search_algo,value='BFS').pack(anchor='w')
        ttk.Label(ctrl,text="Neighbor order:").pack(anchor='w'); orders=['given','ascending','descending','random']; ttk.OptionMenu(ctrl,self.neighbor_order,self.neighbor_order.get(),*orders).pack(anchor='w',pady=2)
        ttk.Separator(ctrl,orient='horizontal').pack(fill='x',pady=6)
        ttk.Label(ctrl,text="Execution",font=('Segoe UI',11,'bold')).pack(anchor='w')
        ttk.Label(ctrl,text="Step delay (ms):").pack(anchor='w'); ttk.Spinbox(ctrl,from_=10,to=3000,textvariable=self.speed_ms,width=8).pack(anchor='w',pady=2)
        ttk.Button(ctrl,text="Generate Graph",command=self.generate_graph,**btn_opts).pack(fill='x',pady=4)
        ttk.Button(ctrl,text="Run (Auto)",command=self.run_auto,**btn_opts).pack(fill='x',pady=2)
        ttk.Button(ctrl,text="Step",command=self.run_step,**btn_opts).pack(fill='x',pady=2)
        ttk.Button(ctrl,text="Reset Search",command=self.reset_run,**btn_opts).pack(fill='x',pady=2)
        ttk.Separator(ctrl,orient='horizontal').pack(fill='x',pady=6)
        edit_row=ttk.Frame(ctrl); edit_row.pack(fill='x',pady=4); ttk.Checkbutton(edit_row,text="Edit Mode",variable=self.edit_mode).pack(side='left')
        ttk.Button(ctrl,text="Undo",command=self.undo,**btn_opts).pack(fill='x',pady=2); ttk.Button(ctrl,text="Redo",command=self.redo,**btn_opts).pack(fill='x',pady=2)
        ttk.Button(ctrl,text="Save Graph",command=self.save_graph,**btn_opts).pack(fill='x',pady=2); ttk.Button(ctrl,text="Load Graph",command=self.load_graph,**btn_opts).pack(fill='x',pady=2)
        ttk.Separator(ctrl,orient='horizontal').pack(fill='x',pady=6)
        ttk.Label(ctrl,text="Start/Goal",font=('Segoe UI',11,'bold')).pack(anchor='w')
        frame_sg=ttk.Frame(ctrl); frame_sg.pack(fill='x',pady=4); ttk.Label(frame_sg,text="Start:").grid(row=0,column=0); self.start_combo=ttk.Combobox(frame_sg,values=[],textvariable=self.start_node,width=6); self.start_combo.grid(row=0,column=1)
        ttk.Label(frame_sg,text="Goal:").grid(row=1,column=0); self.goal_combo=ttk.Combobox(frame_sg,values=[],textvariable=self.goal_node,width=6); self.goal_combo.grid(row=1,column=1)
        ttk.Separator(ctrl,orient='horizontal').pack(fill='x',pady=6)
        ttk.Button(ctrl,text="Run Experiments",command=self.run_experiments,**btn_opts).pack(fill='x',pady=4)
        ttk.Button(ctrl,text="Export Experiments CSV",command=self.export_experiments_csv,**btn_opts).pack(fill='x',pady=2)
        self.results_text=tk.Text(ctrl,width=36,height=18,state='disabled',wrap='word',font=('Segoe UI',10)); self.results_text.pack(pady=4)

    def _create_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(7,7)); self.canvas = FigureCanvasTkAgg(self.fig, master=self); self.canvas.get_tk_widget().pack(side='right', fill='both', expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_click); self.canvas.mpl_connect('button_release_event', self.on_release); self.canvas.mpl_connect('motion_notify_event', self.on_motion); plt.tight_layout()

    def generate_graph(self):
        n = max(5, int(self.node_count.get())); m = max(n-1, int(self.edge_count.get()))
        self.push_undo(); self.G = ensure_connected_graph(n,m,directed=False); self.pos = nx.spring_layout(self.G, seed=42); self.update_node_comboboxes(); self.reset_run(); self.draw_graph()

    def update_node_comboboxes(self):
        nodes = sorted(self.G.nodes()); vals=[str(x) for x in nodes]; self.start_combo['values']=vals; self.goal_combo['values']=vals
        if vals:
            if str(self.start_node.get()) not in vals: self.start_node.set(nodes[0])
            if str(self.goal_node.get()) not in vals: self.goal_node.set(nodes[min(1,len(nodes)-1)])

    def draw_graph(self, highlight_nodes=None, highlight_edges=None, visited=None, frontier=None, path=None):
        self.ax.clear()
        if self.G is None: self.canvas.draw_idle(); return
        undirected_lines=[]; undirected_edges=set(); directed_arrows=[]
        for u,v,data in list(self.G.edges(data=True)):
            if data.get('directed') is False:
                key=tuple(sorted((u,v)))
                if key in undirected_edges: continue
                undirected_edges.add(key); undirected_lines.append((u,v))
            else:
                directed_arrows.append((u,v))
        node_colors=[]; node_sizes=[]
        for n in self.G.nodes():
            if path and n in path: node_colors.append('#7be57b'); node_sizes.append(320)
            elif visited and n in visited: node_colors.append('#bbbbbb'); node_sizes.append(220)
            elif frontier and n in frontier: node_colors.append('#fff79a'); node_sizes.append(240)
            else: node_colors.append('#dddddd'); node_sizes.append(180)
        nx.draw_networkx_nodes(self.G, pos=self.pos, ax=self.ax, node_color=node_colors, node_size=node_sizes)
        nx.draw_networkx_edges(self.G, pos=self.pos, edgelist=undirected_lines, ax=self.ax, edge_color='#888888', arrows=False)
        nx.draw_networkx_edges(self.G, pos=self.pos, edgelist=directed_arrows, ax=self.ax, edge_color='#ff6666', arrows=True, connectionstyle='arc3,rad=0.1')
        nx.draw_networkx_labels(self.G, pos=self.pos, labels={n:str(n) for n in self.G.nodes()}, font_size=8)
        try:
            s=int(self.start_node.get()); g=int(self.goal_node.get())
            if s in self.G.nodes(): nx.draw_networkx_nodes(self.G, pos=self.pos, nodelist=[s], node_color='#ff9999', node_size=400, ax=self.ax)
            if g in self.G.nodes(): nx.draw_networkx_nodes(self.G, pos=self.pos, nodelist=[g], node_color='#9999ff', node_size=400, ax=self.ax)
        except Exception: pass
        if self.selected_source_for_edge is not None and self.selected_source_for_edge in self.G.nodes():
            nx.draw_networkx_nodes(self.G, pos=self.pos, nodelist=[self.selected_source_for_edge], node_color='#ffd27f', node_size=420, ax=self.ax)
        self.ax.set_title(f"Nodes={self.G.number_of_nodes()}  Edges(displayed)={(len(undirected_lines)+len(directed_arrows))}")
        self.ax.axis('off'); self.canvas.draw_idle()

    def push_undo(self):
        if self.G is None: return
        self.undo_stack.append((copy.deepcopy(self.G), copy.deepcopy(self.pos)))
        if len(self.undo_stack)>50: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: self.append_result("Undo empty"); return
        self.redo_stack.append((copy.deepcopy(self.G), copy.deepcopy(self.pos))); G,pos=self.undo_stack.pop(); self.G=G; self.pos=pos; self.update_node_comboboxes(); self.draw_graph(); self.append_result("Undo")

    def redo(self):
        if not self.redo_stack: self.append_result("Redo empty"); return
        self.push_undo(); G,pos=self.redo_stack.pop(); self.G=G; self.pos=pos; self.update_node_comboboxes(); self.draw_graph(); self.append_result("Redo")

    def on_click(self, event):
        if event.inaxes!=self.ax: return
        x,y = event.xdata, event.ydata; node=self._find_node_at_coords((x,y)); edge=self._find_edge_at_coords((x,y))
        if not self.edit_mode.get(): return
        if event.button==3 and node is not None:
            self.push_undo(); self._delete_node(node); self.update_node_comboboxes(); self.draw_graph(); self.append_result(f"Deleted node {node}"); return
        if event.dblclick and node is None:
            self.push_undo(); new_node = max(self.G.nodes())+1 if self.G.nodes() else 0; self.G.add_node(new_node); self.pos[new_node]=(x,y); self.update_node_comboboxes(); self.draw_graph(); self.append_result(f"Added node {new_node}"); return
        if event.dblclick and node is not None:
            self.selected_source_for_edge = node; self.append_result(f"Selected source node {node}"); self.draw_graph(); return
        if event.button==1 and self.selected_source_for_edge is not None and node is not None and node!=self.selected_source_for_edge:
            self.push_undo(); src=self.selected_source_for_edge; tgt=node; self._add_edge_between(src,tgt,directed=self.initial_directed.get()); self.append_result(f"Added edge {src}->{tgt} directed={self.initial_directed.get()}"); self.selected_source_for_edge=None; self.update_node_comboboxes(); self.draw_graph(); return
        if event.button==1 and node is not None and not event.dblclick:
            self.dragging_node=node; self.drag_offset=(self.pos[node][0]-x, self.pos[node][1]-y); return
        if event.button==1 and edge is not None and node is None:
            u,v = edge; data_uv = self.G.get_edge_data(u,v) if self.G.has_edge(u,v) else None; data_vu = self.G.get_edge_data(v,u) if self.G.has_edge(v,u) else None
            self.push_undo()
            if data_uv and data_vu and data_uv.get('directed') is False and data_vu.get('directed') is False:
                self.G.remove_edge(v,u); self.G[u][v]['directed']=True; self.append_result(f"Undirected -> directed {u}->{v}"); self.draw_graph(); return
            if data_uv and data_uv.get('directed') is True and not (data_vu and data_vu.get('directed') is True):
                self.G.remove_edge(u,v); self.G.add_edge(v,u, directed=True); self.append_result(f"Reversed {u}->{v} to {v}->{u}"); self.draw_graph(); return
            if data_vu and data_vu.get('directed') is True and not (data_uv and data_uv.get('directed') is True):
                self.G.remove_edge(v,u); self.G.add_edge(u,v, directed=True); self.append_result(f"Reversed {v}->{u} to {u}->{v}"); self.draw_graph(); return
            if (data_uv and data_uv.get('directed') is True) and not (data_vu):
                self.G.remove_edge(u,v); self.G.add_edge(u,v, directed=False); self.G.add_edge(v,u, directed=False); self.append_result(f"Directed -> undirected ({u},{v})"); self.draw_graph(); return
            if (data_uv or data_vu):
                if not data_uv: self.G.add_edge(u,v, directed=False)
                else: self.G[u][v]['directed']=False
                if not data_vu: self.G.add_edge(v,u, directed=False)
                else: self.G[v][u]['directed']=False
                self.append_result(f"Toggled to undirected ({u},{v})"); self.draw_graph(); return

    def on_release(self, event):
        if self.dragging_node is not None:
            self.push_undo(); self.dragging_node=None; self.draw_graph(); return

    def on_motion(self, event):
        if self.dragging_node is None or event.inaxes!=self.ax: return
        x,y=event.xdata,event.ydata; n=self.dragging_node; self.pos[n]=(x + self.drag_offset[0], y + self.drag_offset[1]); self.draw_graph()

    def _find_node_at_coords(self, point):
        if not self.pos: return None
        x,y = point; min_dist=None; min_node=None
        for n,(nxp,nyp) in self.pos.items():
            d=math.hypot(nxp-x, nyp-y)
            if min_dist is None or d<min_dist: min_dist=d; min_node=n
        xlim=self.ax.get_xlim(); ylim=self.ax.get_ylim(); x_scale=abs(xlim[1]-xlim[0]); y_scale=abs(ylim[1]-ylim[0]); th=self.node_hit_threshold * math.hypot(x_scale,y_scale)
        if min_dist is not None and min_dist<=th: return min_node
        return None

    def _find_edge_at_coords(self, point):
        if self.G is None or not self.pos: return None
        x,y=point; tested=set(); best=None; best_dist=None; best_edge=None
        for u,v,data in self.G.edges(data=True):
            key=(u,v)
            if data.get('directed') is False:
                key = tuple(sorted((u,v)))
                if key in tested: continue
            tested.add(key)
            x1,y1=self.pos[u]; x2,y2=self.pos[v]; seg_len=math.hypot(x2-x1,y2-y1)
            if seg_len==0: continue
            t=((x-x1)*(x2-x1)+(y-y1)*(y2-y1))/(seg_len**2); t=max(0,min(1,t))
            projx=x1+t*(x2-x1); projy=y1+t*(y2-y1); d=math.hypot(projx-x, projy-y)
            xlim=self.ax.get_xlim(); ylim=self.ax.get_ylim(); scale=math.hypot(abs(xlim[1]-xlim[0]), abs(ylim[1]-ylim[0])); th=self.edge_hit_threshold * scale
            if d<=th and (best_dist is None or d<best_dist): best_dist=d; best_edge=(u,v)
        return best_edge

    def _add_edge_between(self,u,v,directed=False):
        if directed: self.G.add_edge(u,v, directed=True)
        else: self.G.add_edge(u,v, directed=False); self.G.add_edge(v,u, directed=False)

    def _delete_node(self,n):
        if n in self.G: self.G.remove_node(n)
        if n in self.pos: del self.pos[n]

    def reset_run(self):
        self.current_generator=None; self.auto_running=False; self.append_result("Reset run"); self.draw_graph()

    def run_step(self):
        if self.G is None: messagebox.showwarning("No graph","Generate or load graph"); return
        if self.current_generator is None:
            try: start=int(self.start_node.get()); goal=int(self.goal_node.get())
            except: messagebox.showwarning("Bad nodes","Start/Goal invalid"); return
            order=self.neighbor_order.get()
            self._start_time = time.time()
            self.current_generator = dfs_generator(self.G,start,goal,neighbor_order=order) if self.search_algo.get()=='DFS' else bfs_generator(self.G,start,goal,neighbor_order=order)
        try:
            state=next(self.current_generator); self._handle_state(state)
        except StopIteration:
            self.append_result("Generator finished"); self.current_generator=None

    def _handle_state(self,state):
        act=state.get('action')
        if act=='init': self.append_result(f"Init: start={state.get('current')}"); self.draw_graph(visited=state.get('visited'))
        elif act=='visit': cur=state.get('current'); self.append_result(f"Visit: {cur} (opened {state.get('opened')})"); self.draw_graph(visited=state.get('visited'), frontier=state.get('stack') if 'stack' in state else state.get('queue'))
        elif act in ('push','enqueue'): self.append_result(f"{act.title()}: {state.get('current')} (opened {state.get('opened')})"); self.draw_graph(visited=state.get('visited'), frontier=state.get('stack') if 'stack' in state else state.get('queue'))
        elif act=='skip': self.append_result(f"Skip {state.get('current')}")
        elif act=='pop': self.append_result(f"Pop {state.get('current')}"); self.draw_graph(visited=state.get('visited'), frontier=state.get('stack'))
        elif act=='found':
            duration = time.time() - self._start_time
            path=state.get('path'); self.append_result(f"Found! length {len(path)}, opened {state.get('opened')}, time: {duration:.4f}s"); self.append_result("Path: "+ " -> ".join(map(str,path))); self.draw_graph(path=path, visited=state.get('visited')); self.current_generator=None
        elif act=='not_found':
            duration = time.time() - self._start_time
            self.append_result(f"Not found, opened {state.get('opened')}, time: {duration:.4f}s"); self.draw_graph(visited=state.get('visited')); self.current_generator=None
        else: self.append_result(str(state)); self.draw_graph()

    def run_auto(self):
        if self.G is None: messagebox.showwarning("No graph","Generate or load graph"); return
        if self.current_generator is None:
            try: start=int(self.start_node.get()); goal=int(self.goal_node.get())
            except: messagebox.showwarning("Bad nodes","Start/Goal invalid"); return
            order=self.neighbor_order.get()
            self._start_time = time.time()
            self.current_generator = dfs_generator(self.G,start,goal,neighbor_order=order) if self.search_algo.get()=='DFS' else bfs_generator(self.G,start,goal,neighbor_order=order)
        if self.auto_running: self.auto_running=False; self.append_result("Auto stopped"); return
        self.auto_running=True; self.step_delay=max(10,int(self.speed_ms.get())); self.append_result("Auto started"); self._auto_step()

    def _auto_step(self):
        if not self.auto_running or self.current_generator is None: self.auto_running=False; return
        try: state=next(self.current_generator); self._handle_state(state)
        except StopIteration: self.append_result("Auto finished"); self.current_generator=None; self.auto_running=False; return
        self.master.after(self.step_delay, self._auto_step)

    def save_graph(self):
        if self.G is None: messagebox.showwarning("No graph","Nothing to save"); return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json'),('Edge list','*.edgelist')])
        if not path: return
        if path.endswith('.json'):
            data={'nodes':[],'edges':[]}
            for n in self.G.nodes(): data['nodes'].append({'id':n,'pos':self.pos.get(n,(0,0))})
            for u,v,d in self.G.edges(data=True): data['edges'].append({'u':u,'v':v,'directed': d.get('directed',True)})
            with open(path,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
            self.append_result(f"Saved {path}")
        else:
            with open(path,'w',encoding='utf-8') as f:
                for u,v,d in self.G.edges(data=True): f.write(f"{u} {v} {int(d.get('directed',1))}\n")
            self.append_result(f"Saved edgelist {path}")

    def load_graph(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json'),('Edge list','*.edgelist')])
        if not path: return
        try:
            if path.endswith('.json'):
                with open(path,'r',encoding='utf-8') as f: data=json.load(f)
                self.push_undo(); G=nx.DiGraph(); pos={}
                for n in data.get('nodes',[]): G.add_node(n['id']); pos[n['id']]=tuple(n.get('pos',(0,0)))
                for e in data.get('edges',[]): u=e['u']; v=e['v']; directed=e.get('directed',True)
                for e in data.get('edges',[]):
                    u=e['u']; v=e['v']; directed=e.get('directed',True)
                    if directed: G.add_edge(u,v,directed=True)
                    else: G.add_edge(u,v,directed=False); G.add_edge(v,u,directed=False)
                self.G=G; self.pos=pos; self.update_node_comboboxes(); self.draw_graph(); self.append_result(f"Loaded {path}\n")
            else:
                with open(path,'r',encoding='utf-8') as f: lines=[l.strip() for l in f if l.strip()]
                self.push_undo(); G=nx.DiGraph(); nodes=set()
                for line in lines:
                    parts=line.split(); u=int(parts[0]); v=int(parts[1]); d=int(parts[2]) if len(parts)>2 else 1
                    nodes.add(u); nodes.add(v)
                    if d==1: G.add_edge(u,v,directed=True)
                    else: G.add_edge(u,v,directed=False); G.add_edge(v,u,directed=False)
                for n in nodes: G.add_node(n)
                self.G=G; self.pos={n:(random.random(),random.random()) for n in self.G.nodes()}; self.update_node_comboboxes(); self.draw_graph(); self.append_result(f"Loaded edgelist {path}\n")
        except Exception as e:
            messagebox.showerror("Load error\n", str(e))

    def run_experiments(self):
        if self.G is None: messagebox.showwarning("No graph\n","Generate a graph\n"); return
        n=max(5,int(self.node_count.get())); m=max(n-1,int(self.edge_count.get())); results=[]
        tree=ensure_connected_graph(n,n-1,directed=False); und=ensure_connected_graph(n,m,directed=False); dirg=ensure_connected_graph(n,m,directed=True)
        variants=[('Tree',tree),('Undirected',und),('Directed',dirg)]
        for name,g in variants:
            for algo in ('DFS','BFS'):
                start=0; goal=n-1
                _start_time = time.time()
                gen = dfs_generator(g,start,goal,neighbor_order=self.neighbor_order.get()) if algo=='DFS' else bfs_generator(g,start,goal,neighbor_order=self.neighbor_order.get())
                found=False; pathlen=0; opened=0
                for state in gen:
                    if state.get('action')=='found':
                        found=True; pathlen=len(state.get('path',[])); opened=state.get('opened',0); break
                    if state.get('action')=='not_found':
                        found=False; opened=state.get('opened',0); break
                duration = time.time() - _start_time
                results.append({'variant':name,'algo':algo,'found':found,'pathlen':pathlen,'opened':opened, 'time':duration})
        self.experiments=results; self.append_result("Experiments:\n"); 
        for r in results: self.append_result(f"{r['variant']:10s} | {r['algo']:3s} | found={r['found']} | pathlen={r['pathlen']} | opened={r['opened']} | time={r['time']:.4f}s\n")

    def export_experiments_csv(self):
        if not hasattr(self,'experiments') or not self.experiments: messagebox.showwarning('No data','Run experiments'); return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if not path: return
        keys=['variant','algo','found','pathlen','opened','time']
        try:
            with open(path,'w',newline='',encoding='utf-8') as f: writer=csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows(self.experiments)
            self.append_result(f"Exported to {path}\n")
        except Exception as e: messagebox.showerror('Save error', str(e))

    def append_result(self,text):
        self.results_text.configure(state='normal'); self.results_text.insert('end', text+'\n'); self.results_text.see('end'); self.results_text.configure(state='disabled')

def main():
    root=tk.Tk(); root.geometry('1200x780'); app=GraphSearchApp(root); root.mainloop()

if __name__=='__main__':
    main()