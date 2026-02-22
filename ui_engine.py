import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import webbrowser
import os
from PIL import Image, ImageTk, ImageOps

class UIHelper:
    @staticmethod
    def hex_to_rgba(hex_color, alpha=150):
        hex_color = str(hex_color).strip().lstrip('#')
        if len(hex_color) == 6:
            try: return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
            except: pass
        return (20, 20, 20, alpha)

class BasePage:
    def __init__(self, main_window):
        self.mw = main_window 
        self.canvas = main_window.canvas
        self.widgets = [] 

    def render(self, start_x, w, h): pass
    def on_mousewheel(self, dy): pass
    
    def clear(self):
        for w in self.widgets:
            try: w.destroy()
            except: pass
        self.widgets.clear()

class DashboardPage(BasePage):
    def render(self, start_x, w, h):
        cfg = self.mw.app_context.config_mgr.data
        state = self.mw.app_context.state
        registry = self.mw.app_context.registry
        
        card_w = w - start_x - 30
        if card_w < 200: return
        
        card_rgba = UIHelper.hex_to_rgba(cfg.get("card_color", "#141414"), 130)
        t_font = (cfg["font_title"], int(cfg["size_title"]), "bold")
        t_color = cfg["color_title"]
        c_font = (cfg["font_content"], int(cfg["size_content"]))
        c_color = cfg["color_content"]
        line_height = int(cfg["size_content"]) * 1.8

        current_y = 100
        
        for mod_key in cfg["module_order"]:
            if not cfg["module_visibility"].get(mod_key, True): continue
            mod = registry.module_dict.get(mod_key)
            if not mod: continue
            
            lines_data = mod.generate_lines(state, webbrowser.open, self.mw.safe_open_registration)
            card_h = 45 + len(lines_data) * line_height + 15

            self.mw.draw_transparent_panel(f"card_{mod_key}", start_x, current_y, card_w, card_h, card_rgba, tags=("page_content", "dash_scroll"))
            self.canvas.create_text(start_x + 15, current_y + 20, text=mod.default_name, fill=t_color, font=t_font, anchor="w", tags=("page_content", "dash_scroll"))
            
            text_y = current_y + 45
            for text, action in lines_data:
                self.mw.make_clickable_text(start_x + 15, text_y, text, c_color, c_font, ("page_content", "dash_scroll"), action)
                text_y += line_height
            current_y += card_h + 15
            
        self.mw.dash_max_scroll = max(0, current_y - 100 - (h - 120))

        h_font = (cfg.get("font_header", "Microsoft YaHei"), int(cfg.get("size_header", 16)), "bold")
        h_color = cfg.get("color_header", "#FFFFFF")
        
        self.mw.draw_transparent_panel("dash_header", start_x, 20, card_w, 60, card_rgba, tags="page_content")
        self.canvas.create_text(start_x + 20, 50, text="📊 统计数据", fill=h_color, font=h_font, anchor="w", tags="page_content")
        
        handle = cfg.get("handle", "")
        greet = f"{handle}，欢迎回来。" if handle else "请前往系统设置配置"
        btn_x = start_x + card_w - 20
        prof_url = f"https://codeforces.com/profile/{handle}" if handle else None
        txt_greet = self.mw.make_clickable_text(btn_x, 50, greet, c_color, c_font, "page_content", lambda u=prof_url: webbrowser.open(u) if u else None)
        self.canvas.itemconfig(txt_greet, anchor="e")

    def on_mousewheel(self, dy):
        if self.mw.dash_max_scroll <= 0: return
        new_offset = self.mw.dash_y_offset + dy
        if new_offset < 0: dy = -self.mw.dash_y_offset; self.mw.dash_y_offset = 0
        elif new_offset > self.mw.dash_max_scroll: dy = self.mw.dash_max_scroll - self.mw.dash_y_offset; self.mw.dash_y_offset = self.mw.dash_max_scroll
        else: self.mw.dash_y_offset = new_offset
        self.canvas.move("dash_scroll", 0, -dy)

class WrongPage(BasePage):
    def render(self, start_x, w, h):
        cfg = self.mw.app_context.config_mgr.data
        card_w = w - start_x - 30
        if card_w < 100: return

        card_hex = cfg.get("card_color", "#141414")
        card_rgba = UIHelper.hex_to_rgba(card_hex, 130)

        h_font = (cfg.get("font_header", "Microsoft YaHei"), int(cfg.get("size_header", 16)), "bold")
        t_font = (cfg["font_title"], int(cfg["size_title"]), "bold")
        c_font = (cfg["font_content"], int(cfg["size_content"]))

        self.mw.draw_transparent_panel("wrong_header", start_x, 20, card_w, h - 40, card_rgba, tags="page_content")
        self.canvas.create_text(start_x + 20, 50, text="📚 错题集 (双击跳转)", fill=cfg.get("color_header"), font=h_font, anchor="w", tags="page_content")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=card_hex, fieldbackground=card_hex, foreground="white", borderwidth=0, font=c_font)
        style.configure("Treeview.Heading", background="white", foreground="black", font=t_font, borderwidth=0)

        self.tree_frame = tk.Frame(self.canvas, bg=card_hex)
        self.widgets.append(self.tree_frame)
        
        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Name", "Verdict"), show="headings")
        self.tree.heading("ID", text="题号"); self.tree.column("ID", width=80, anchor="center")
        self.tree.heading("Name", text="题目"); self.tree.column("Name", width=int(card_w*0.5), anchor="w")
        self.tree.heading("Verdict", text="状态"); self.tree.column("Verdict", width=150, anchor="center")
        
        scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._on_db_click)

        self.canvas.create_window(start_x + 20, 80, window=self.tree_frame, anchor="nw", width=card_w-40, height=h-120, tags="page_content")
        self.refresh_data_ui()

    def refresh_data_ui(self):
        if not hasattr(self, 'tree'): return
        wrong_list = self.mw.app_context.state.wrong_list
        for item in self.tree.get_children(): self.tree.delete(item)
        if not wrong_list: self.tree.insert("", "end", values=("无", "近期无做错的记录", ""))
        else:
            for p in wrong_list: self.tree.insert("", "end", values=(p['id'], p['name'], p['verdict']))

    def _on_db_click(self, e):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']
        if val and "..." not in str(val[0]):
            m = __import__('re').match(r"(\d+)([A-Za-z]\d*)", str(val[0]))
            if m: webbrowser.open(f"https://codeforces.com/contest/{m.group(1)}/problem/{m.group(2)}")

class SettingsPage(BasePage):
    def render(self, start_x, w, h):
        cfg = self.mw.app_context.config_mgr.data
        card_w = w - start_x - 30
        if card_w < 100: return

        card_hex = cfg.get("card_color", "#141414")
        h_font = (cfg.get("font_header", "Microsoft YaHei"), int(cfg.get("size_header", 16)), "bold")
        t_font = (cfg["font_title"], int(cfg["size_title"]), "bold")
        c_font = (cfg["font_content"], int(cfg["size_content"]))

        self.mw.draw_transparent_panel("set_header", start_x, 20, card_w, h - 40, UIHelper.hex_to_rgba(card_hex, 150), tags="page_content")
        self.canvas.create_text(start_x + 20, 50, text="⚙️ 系统设置", fill=cfg.get("color_header"), font=h_font, anchor="w", tags="page_content")

        self.container = tk.Frame(self.canvas, bg=card_hex)
        self.widgets.append(self.container)
        
        self.set_canv = tk.Canvas(self.container, bg=card_hex, highlightthickness=0)
        v_scr = ttk.Scrollbar(self.container, orient="vertical", command=self.set_canv.yview)
        h_scr = ttk.Scrollbar(self.container, orient="horizontal", command=self.set_canv.xview)
        self.set_canv.configure(yscrollcommand=v_scr.set, xscrollcommand=h_scr.set)

        self.set_canv.grid(row=0, column=0, sticky="nsew")
        v_scr.grid(row=0, column=1, sticky="ns")
        h_scr.grid(row=1, column=0, sticky="ew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        scroll_frame = tk.Frame(self.set_canv, bg=card_hex)
        self.set_canv.create_window((0, 0), window=scroll_frame, anchor="nw")
        scroll_frame.bind("<Configure>", lambda e: self.set_canv.configure(scrollregion=self.set_canv.bbox("all")))

        self.canvas.create_window(start_x + 20, 80, window=self.container, anchor="nw", width=card_w-40, height=h-120, tags="page_content")
        
        kw_l = {"bg": card_hex, "fg": cfg["color_content"], "font": c_font}
        kw_b = {"relief": "groove", "bg": "#4DA8DA", "fg": "white", "font": c_font}

        self._build_visual_settings(scroll_frame, kw_l, kw_b, cfg["color_title"], t_font, c_font)
        self._build_font_settings(scroll_frame, kw_l, kw_b, cfg["color_title"], t_font, c_font, card_hex)
        self._build_module_settings(scroll_frame, kw_b, cfg["color_title"], t_font, c_font, card_hex)
        self._build_api_settings(scroll_frame, kw_l, cfg["color_title"], t_font, c_font, cfg["color_content"], card_hex)

        tk.Button(scroll_frame, text="💾 保存并应用所有设置", command=self.save, **kw_b).pack(pady=20, fill="x", padx=50)

    def _build_visual_settings(self, parent, lbl_kw, btn_kw, t_color, t_font, c_font):
        lf1 = tk.LabelFrame(parent, text=" 🎨 颜色与背景 ", bg=lbl_kw["bg"], fg=t_color, font=t_font)
        lf1.pack(fill=tk.X, pady=10, padx=10, ipadx=5, ipady=5)
        tk.Label(lf1, text="窗口大小:", **lbl_kw).grid(row=0, column=0, pady=5, sticky="e")
        self.ent_win = tk.Entry(lf1, width=15, font=c_font); self.ent_win.insert(0, self.mw.app_context.config_mgr.data.get("window_size", "950x650"))
        self.ent_win.grid(row=0, column=1, pady=5, sticky="w", padx=5)
        tk.Button(lf1, text="选择背景图", command=self.pick_bg_image, **btn_kw).grid(row=0, column=2, padx=5)
        tk.Button(lf1, text="清除背景", command=lambda: self.mw.app_context.config_mgr.data.update({"bg_image": ""}) or self.mw.force_render_all(), **btn_kw).grid(row=0, column=3, padx=5)
        tk.Label(lf1, text="侧栏底色(Hex):", **lbl_kw).grid(row=1, column=0, pady=5, sticky="e")
        self.ent_side_c = tk.Entry(lf1, width=15, font=c_font); self.ent_side_c.insert(0, self.mw.app_context.config_mgr.data.get("sidebar_color", ""))
        self.ent_side_c.grid(row=1, column=1, pady=5, sticky="w", padx=5)
        tk.Button(lf1, text="选取", command=lambda: self.choose_color_for_entry(self.ent_side_c), **btn_kw).grid(row=1, column=2, sticky="w", padx=5)
        tk.Label(lf1, text="卡片底色(Hex):", **lbl_kw).grid(row=1, column=3, pady=5, sticky="e")
        self.ent_card_c = tk.Entry(lf1, width=15, font=c_font); self.ent_card_c.insert(0, self.mw.app_context.config_mgr.data.get("card_color", ""))
        self.ent_card_c.grid(row=1, column=4, pady=5, sticky="w", padx=5)
        tk.Button(lf1, text="选取", command=lambda: self.choose_color_for_entry(self.ent_card_c), **btn_kw).grid(row=1, column=5, sticky="w", padx=5)

    def _build_font_settings(self, parent, lbl_kw, btn_kw, t_color, t_font, c_font, card_hex):
        cfg = self.mw.app_context.config_mgr.data
        lf2 = tk.LabelFrame(parent, text=" 🔠 字体设置 ", bg=card_hex, fg=t_color, font=t_font)
        lf2.pack(fill=tk.X, pady=10, padx=10, ipadx=5, ipady=5)
        fonts = ["Microsoft YaHei", "Arial", "Consolas", "SimHei"]
        
        tk.Label(lf2, text="大标题字体:", **lbl_kw).grid(row=0, column=0, pady=5, sticky="e")
        self.cb_h_font = ttk.Combobox(lf2, values=fonts, width=12, font=c_font)
        self.cb_h_font.set(cfg.get("font_header", "Microsoft YaHei")); self.cb_h_font.grid(row=0, column=1, padx=5)
        tk.Label(lf2, text="字号:", **lbl_kw).grid(row=0, column=2, sticky="e")
        self.ent_h_size = tk.Entry(lf2, width=5, font=c_font); self.ent_h_size.insert(0, str(cfg.get("size_header", 16)))
        self.ent_h_size.grid(row=0, column=3, sticky="w", padx=5)
        tk.Label(lf2, text="颜色:", **lbl_kw).grid(row=0, column=4, sticky="e")
        self.ent_h_col = tk.Entry(lf2, width=10, font=c_font); self.ent_h_col.insert(0, cfg.get("color_header", "#FFFFFF"))
        self.ent_h_col.grid(row=0, column=5, sticky="w", padx=5)
        tk.Button(lf2, text="选取", command=lambda: self.choose_color_for_entry(self.ent_h_col), **btn_kw).grid(row=0, column=6, padx=5)

        tk.Label(lf2, text="次级标题字体:", **lbl_kw).grid(row=1, column=0, pady=5, sticky="e")
        self.cb_t_font = ttk.Combobox(lf2, values=fonts, width=12, font=c_font)
        self.cb_t_font.set(cfg["font_title"]); self.cb_t_font.grid(row=1, column=1, padx=5)
        tk.Label(lf2, text="字号:", **lbl_kw).grid(row=1, column=2, sticky="e")
        self.ent_t_size = tk.Entry(lf2, width=5, font=c_font); self.ent_t_size.insert(0, str(cfg["size_title"]))
        self.ent_t_size.grid(row=1, column=3, sticky="w", padx=5)
        tk.Label(lf2, text="颜色:", **lbl_kw).grid(row=1, column=4, sticky="e")
        self.ent_t_col = tk.Entry(lf2, width=10, font=c_font); self.ent_t_col.insert(0, cfg["color_title"])
        self.ent_t_col.grid(row=1, column=5, sticky="w", padx=5)
        tk.Button(lf2, text="选取", command=lambda: self.choose_color_for_entry(self.ent_t_col), **btn_kw).grid(row=1, column=6, padx=5)

        tk.Label(lf2, text="内容小字字体:", **lbl_kw).grid(row=2, column=0, pady=5, sticky="e")
        self.cb_c_font = ttk.Combobox(lf2, values=fonts, width=12, font=c_font)
        self.cb_c_font.set(cfg["font_content"]); self.cb_c_font.grid(row=2, column=1, padx=5)
        tk.Label(lf2, text="字号:", **lbl_kw).grid(row=2, column=2, sticky="e")
        self.ent_c_size = tk.Entry(lf2, width=5, font=c_font); self.ent_c_size.insert(0, str(cfg["size_content"]))
        self.ent_c_size.grid(row=2, column=3, sticky="w", padx=5)
        tk.Label(lf2, text="颜色:", **lbl_kw).grid(row=2, column=4, sticky="e")
        self.ent_c_col = tk.Entry(lf2, width=10, font=c_font); self.ent_c_col.insert(0, cfg["color_content"])
        self.ent_c_col.grid(row=2, column=5, sticky="w", padx=5)
        tk.Button(lf2, text="选取", command=lambda: self.choose_color_for_entry(self.ent_c_col), **btn_kw).grid(row=2, column=6, padx=5)

    def _build_module_settings(self, parent, btn_kw, t_color, t_font, c_font, card_hex):
        cfg = self.mw.app_context.config_mgr.data
        lf_sort = tk.LabelFrame(parent, text=" 📌 模块定制 ", bg=card_hex, fg=t_color, font=t_font)
        lf_sort.pack(fill=tk.X, pady=10, padx=10, ipadx=5, ipady=5)
        self.listbox = tk.Listbox(lf_sort, width=40, height=4, font=c_font, bg="white", fg="black", selectbackground="#4DA8DA")
        self.listbox.pack(side=tk.LEFT, padx=10, pady=10)
        self.key_mapping = []
        registry = self.mw.app_context.registry
        for k in cfg["module_order"]:
            status = "👁️" if cfg["module_visibility"].get(k, True) else "❌"
            mod = registry.module_dict.get(k)
            if mod:
                self.listbox.insert(tk.END, f"{status} {mod.default_name.split(' (')[0]}")
                self.key_mapping.append(k)
        btn_f = tk.Frame(lf_sort, bg=card_hex)
        btn_f.pack(side=tk.LEFT, padx=10)
        tk.Button(btn_f, text="⬆ 上移", command=self.move_up, **btn_kw).pack(pady=2, fill=tk.X)
        tk.Button(btn_f, text="⬇ 下移", command=self.move_down, **btn_kw).pack(pady=2, fill=tk.X)
        tk.Button(btn_f, text="👁️显示/隐藏", command=self.toggle_visibility, **btn_kw).pack(pady=2, fill=tk.X)

    def _build_api_settings(self, parent, lbl_kw, t_color, t_font, c_font, c_color, card_hex):
        cfg = self.mw.app_context.config_mgr.data
        lf3 = tk.LabelFrame(parent, text=" ⚙️ API与个性化设置 ", bg=card_hex, fg=t_color, font=t_font)
        lf3.pack(fill=tk.X, pady=10, padx=10, ipadx=5, ipady=5)
        tk.Label(lf3, text="Handle(ID):", **lbl_kw).grid(row=0, column=0, sticky="e", pady=5)
        self.ent_h = tk.Entry(lf3, font=c_font, width=15); self.ent_h.insert(0, cfg.get("handle", ""))
        self.ent_h.grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(lf3, text="刷新频率(秒):", **lbl_kw).grid(row=0, column=2, sticky="e")
        self.ent_rate = tk.Entry(lf3, font=c_font, width=6); self.ent_rate.insert(0, str(cfg.get("refresh_rate", 60)))
        self.ent_rate.grid(row=0, column=3, sticky="w", padx=5)
        tk.Label(lf3, text="近期rating变更(次):", **lbl_kw).grid(row=0, column=4, sticky="e")
        self.ent_rn = tk.Entry(lf3, font=c_font, width=6); self.ent_rn.insert(0, str(cfg.get("rating_n", 5)))
        self.ent_rn.grid(row=0, column=5, sticky="w", padx=5)
        tk.Label(lf3, text="API Key:", **lbl_kw).grid(row=1, column=0, sticky="e", pady=5)
        self.ent_k = tk.Entry(lf3, show="*", font=c_font, width=25); self.ent_k.insert(0, cfg.get("api_key", ""))
        self.ent_k.grid(row=1, column=1, columnspan=3, sticky="w", padx=5)
        tk.Label(lf3, text="近期开始比赛(场):", **lbl_kw).grid(row=1, column=4, sticky="e")
        self.ent_cn = tk.Entry(lf3, font=c_font, width=6); self.ent_cn.insert(0, str(cfg.get("contest_n", 5)))
        self.ent_cn.grid(row=1, column=5, sticky="w", padx=5)
        tk.Label(lf3, text="API Secret:", **lbl_kw).grid(row=2, column=0, sticky="e", pady=5)
        self.ent_s = tk.Entry(lf3, show="*", font=c_font, width=25); self.ent_s.insert(0, cfg.get("api_secret", ""))
        self.ent_s.grid(row=2, column=1, columnspan=3, sticky="w", padx=5)
        tk.Label(lf3, text="比赛筛选(多选):", **lbl_kw).grid(row=3, column=0, pady=10, sticky="e")
        f_frame = tk.Frame(lf3, bg=card_hex)
        f_frame.grid(row=3, column=1, columnspan=5, sticky="w", padx=5)
        self.f_vars = {}
        for f_type in ["All", "Div. 1", "Div. 2", "Div. 3", "Div. 4", "Educational"]:
            v = tk.BooleanVar(value=(f_type in cfg.get("contest_filters", ["All"])))
            tk.Checkbutton(f_frame, text=f_type, variable=v, bg=card_hex, fg=c_color, font=c_font, selectcolor="#444").pack(side=tk.LEFT)
            self.f_vars[f_type] = v

    def save(self):
        cfg = self.mw.app_context.config_mgr.data
        cfg["handle"] = self.ent_h.get().strip()
        cfg["api_key"] = self.ent_k.get().strip()
        cfg["api_secret"] = self.ent_s.get().strip()
        cfg["window_size"] = self.ent_win.get().strip()
        cfg["sidebar_color"] = self.ent_side_c.get().strip()
        cfg["card_color"] = self.ent_card_c.get().strip()
        cfg["font_header"] = self.cb_h_font.get(); cfg["size_header"] = self.ent_h_size.get(); cfg["color_header"] = self.ent_h_col.get().strip()
        cfg["font_title"] = self.cb_t_font.get(); cfg["size_title"] = self.ent_t_size.get(); cfg["color_title"] = self.ent_t_col.get().strip()
        cfg["font_content"] = self.cb_c_font.get(); cfg["size_content"] = self.ent_c_size.get(); cfg["color_content"] = self.ent_c_col.get().strip()
        cfg["module_order"] = self.key_mapping
        sel_f = [k for k, v in self.f_vars.items() if v.get()]
        cfg["contest_filters"] = sel_f if sel_f else ["All"]
        try: cfg["refresh_rate"] = max(2, int(self.ent_rate.get().strip()))
        except: pass
        try: cfg["rating_n"] = int(self.ent_rn.get().strip())
        except: pass
        try: cfg["contest_n"] = int(self.ent_cn.get().strip())
        except: pass
        
        self.mw.app_context.config_mgr.save()
        self.mw.app_context.service.update_spider_auth()
        try: self.mw.root.geometry(cfg["window_size"])
        except: pass
        
        self.mw.force_render_all()
        self.mw.app_context.trigger_global_refresh()
        messagebox.showinfo("成功", "设置已保存")

    def on_mousewheel(self, dy):
        if hasattr(self, 'set_canv'): self.set_canv.yview_scroll(int(dy/10), "units")

    def choose_color_for_entry(self, entry):
        c = colorchooser.askcolor(initialcolor=entry.get().strip() or None)[1]
        if c: entry.delete(0, tk.END); entry.insert(0, c)

    def pick_bg_image(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.png;*.jpg;*.jpeg")])
        if p: 
            self.mw.app_context.config_mgr.data["bg_image"] = p
            self.mw.force_render_all()

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0: return
        idx = sel[0]; val = self.listbox.get(idx)
        self.listbox.delete(idx); self.listbox.insert(idx-1, val); self.listbox.selection_set(idx-1)
        self.key_mapping[idx], self.key_mapping[idx-1] = self.key_mapping[idx-1], self.key_mapping[idx]

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == self.listbox.size() - 1: return
        idx = sel[0]; val = self.listbox.get(idx)
        self.listbox.delete(idx); self.listbox.insert(idx+1, val); self.listbox.selection_set(idx+1)
        self.key_mapping[idx], self.key_mapping[idx+1] = self.key_mapping[idx+1], self.key_mapping[idx]

    def toggle_visibility(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]; key = self.key_mapping[idx]
        cfg = self.mw.app_context.config_mgr.data
        cfg["module_visibility"][key] = not cfg["module_visibility"].get(key, True)
        status = "👁️" if cfg["module_visibility"][key] else "❌"
        mod = self.mw.app_context.registry.module_dict.get(key)
        self.listbox.delete(idx)
        self.listbox.insert(idx, f"{status} {mod.default_name.split(' (')[0]}")
        self.listbox.selection_set(idx)

class MainWindow:
    def __init__(self, root, app_context):
        self.root = root
        self.app_context = app_context
        
        self.images = {}
        self.dash_y_offset = 0
        self.dash_max_scroll = 0
        self.current_page_id = "dashboard"
        
        self.canvas = tk.Canvas(self.root, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        
        self.pages = {
            "dashboard": DashboardPage(self),
            "wrong": WrongPage(self),
            "settings": SettingsPage(self)
        }
        
        self.root.bind("<MouseWheel>", self._on_scroll)
        self.root.bind("<Button-4>", self._on_scroll)
        self.root.bind("<Button-5>", self._on_scroll)

    def _on_resize(self, e):
        if hasattr(self, '_t'): self.root.after_cancel(self._t)
        self._t = self.root.after(150, lambda: self.force_render_all())

    def _on_scroll(self, event):
        dy = -30 if event.num == 4 or getattr(event, 'delta', 0) > 0 else 30 if event.num == 5 or getattr(event, 'delta', 0) < 0 else 0
        if dy != 0: self.pages[self.current_page_id].on_mousewheel(dy)

    def switch_page(self, pid, force_redraw=False):
        if pid not in self.pages or (pid == self.current_page_id and not force_redraw): return
        self.pages[self.current_page_id].clear()
        self.current_page_id = pid
        self.canvas.delete("page_content")
        self.dash_y_offset = 0
        self.pages[pid].render(210, self.canvas.winfo_width(), self.canvas.winfo_height())

    def force_render_all(self):
        """仅在窗口缩放、换背景时调用的全局重绘"""
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.delete("all")
        self.images.clear()
        
        cfg = self.app_context.config_mgr.data
        if cfg.get("bg_image") and os.path.exists(cfg["bg_image"]):
            try:
                self.images["bg"] = ImageTk.PhotoImage(ImageOps.fit(Image.open(cfg["bg_image"]), (w, h), Image.Resampling.LANCZOS))
                self.canvas.create_image(0, 0, anchor="nw", image=self.images["bg"])
            except: pass
            
        self.pages[self.current_page_id].clear()
        self.pages[self.current_page_id].render(210, w, h)
        self._render_sidebar(h, cfg)

    def _render_sidebar(self, h, cfg):
        self.draw_transparent_panel("sidebar", 0, 0, 180, h, UIHelper.hex_to_rgba(cfg["sidebar_color"], 140))
        
        # 提前预留好头像的坑位和 ID
        self.canvas.create_oval(50, 20, 130, 100, outline="gray", width=2)
        self.avatar_img_id = self.canvas.create_image(90, 60)
        self.avatar_text_id = self.canvas.create_text(90, 60, text="无头像", fill="gray", font=("Arial", 10))

        pil_img = self.app_context.state.avatar_pil
        if pil_img:
            self.images["avatar"] = ImageTk.PhotoImage(pil_img)
            self.canvas.itemconfig(self.avatar_img_id, image=self.images["avatar"])
            self.canvas.itemconfig(self.avatar_text_id, text="")

        self.time_label_id = self.canvas.create_text(90, 130, text="--:--:--", fill="white", font=("Consolas", 11), justify="center")
        self.canvas.create_rectangle(35, 146, 145, 174, fill="#0A0A0A", outline="#444444", width=2)
        ac_text = f"AC: {self.app_context.state.ac_count}"
        self.ac_label_id = self.canvas.create_text(90, 160, text=ac_text, fill="#FFD700", font=("Consolas", 13, "bold"), justify="center")

        navs = [("dashboard", "📊 实时看板"), ("wrong", "📚 错题集"), ("settings", "⚙️ 系统设置")]
        for idx, (pid, text) in enumerate(navs):
            self.create_canvas_button(90, 210 + idx*50, text, lambda e, p=pid: self.switch_page(p))

        # 状态文字与刷新按钮 (移至最底部)
        state = self.app_context.state
        self.status_lbl_id = self.canvas.create_text(90, h - 70, text=state.status_msg, fill="#FF6B6B" if state.status_is_err else "#00FF7F", font=("Arial", 9), justify="center")
        refresh_id = self.canvas.create_text(90, h - 30, text="[🔄 全局刷新]", fill="#1238E2", font=("Microsoft YaHei", 10, "bold"), justify="center")
        self.canvas.tag_bind(refresh_id, "<Button-1>", lambda e: self.app_context.trigger_global_refresh())
        self.canvas.tag_bind(refresh_id, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(refresh_id, "<Leave>", lambda e: self.canvas.config(cursor=""))

    def refresh_data_ui(self):
        """刷新页面"""
        
        # 处于“数据看板”或“错题本”时重绘主区域
        if self.current_page_id in ["dashboard", "wrong"]:
            self.switch_page(self.current_page_id, force_redraw=True)
            
        state = self.app_context.state
        
        # 局部更新侧边栏头像 (不受页面限制，全局更新)
        if state.avatar_pil and hasattr(self, 'avatar_img_id'):
            self.images["avatar"] = ImageTk.PhotoImage(state.avatar_pil)
            self.canvas.itemconfig(self.avatar_img_id, image=self.images["avatar"])
            self.canvas.itemconfig(self.avatar_text_id, text="")
            
        # 局部更新侧边栏状态文字 (不受页面限制，全局更新)
        if hasattr(self, 'status_lbl_id'):
            self.canvas.itemconfig(self.status_lbl_id, text=state.status_msg, fill="#FF6B6B" if state.status_is_err else "#00FF7F")

        if hasattr(self, 'ac_label_id'):
            self.canvas.itemconfig(self.ac_label_id, text=f"AC: {state.ac_count}")

    def draw_transparent_panel(self, key_name, x, y, w, h, overlay_color, tags=None):
        if w <= 0 or h <= 0: return
        self.images[f"glass_{key_name}"] = ImageTk.PhotoImage(Image.new("RGBA", (int(w), int(h)), overlay_color))
        self.canvas.create_image(x, y, anchor="nw", image=self.images[f"glass_{key_name}"], tags=tags)

    def create_canvas_button(self, x, y, text, cmd):
        txt_id = self.canvas.create_text(x, y, text=text, fill="white", font=("Microsoft YaHei", 12, "bold"))
        self.canvas.tag_bind(txt_id, "<Button-1>", cmd)
        self.canvas.tag_bind(txt_id, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(txt_id, "<Leave>", lambda e: self.canvas.config(cursor=""))

    def make_clickable_text(self, x, y, text, color, font, tags, action):
        txt_id = self.canvas.create_text(x, y, text=text, fill=color, font=font, anchor="w", tags=tags)
        if action:
            self.canvas.tag_bind(txt_id, "<Double-1>", lambda e: action())
            self.canvas.tag_bind(txt_id, "<Enter>", lambda e: self.canvas.itemconfig(txt_id, fill="#4DA8DA") or self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(txt_id, "<Leave>", lambda e: self.canvas.itemconfig(txt_id, fill=color) or self.canvas.config(cursor=""))
        return txt_id

    def safe_open_registration(self, contest_id):
        def _check():
            ok, url = self.app_context.service.check_contest_registration(contest_id)
            if not ok: self.root.after(0, lambda: messagebox.showinfo("提示", "该比赛尚未开始报名！"))
            else: webbrowser.open(url)
        self.app_context.executor.submit(_check)