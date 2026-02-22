import tkinter as tk
from datetime import datetime

from core_engine import ConfigManager, AppState, TaskExecutor, CFDataService, ModuleRegistry
from ui_engine import MainWindow

class AppContext:
    def __init__(self):
        self.config_mgr = ConfigManager()
        self.state = AppState()
        self.executor = TaskExecutor(max_workers=3)
        self.service = CFDataService(self.config_mgr, self.state)
        self.registry = ModuleRegistry()
        
        self.on_ui_refresh_needed = None 

    def trigger_global_refresh(self):
        if not self.config_mgr.data.get("handle"): return
        
        self.state.status_msg = "状态: 请求网络中..."
        self.state.status_is_err = False
        if self.on_ui_refresh_needed: self.on_ui_refresh_needed()

        def _worker():
            try:
                with self.service.fetch_lock:
                    self.service.fetch_all_dashboard_data()
                    self.service.fetch_wrong_problems()
                    
                self.state.status_msg = f"状态: 已同步 ({datetime.now().strftime('%H:%M:%S')})"
                self.state.status_is_err = False
            except Exception as e:
                #print(f"Fetch Error: {e}")         #报错输出
                self.state.status_msg = "状态: 获取失败，请检查网络"
                self.state.status_is_err = True
            
            if self.on_ui_refresh_needed: self.on_ui_refresh_needed()

        self.executor.submit(_worker)

class MainApplication:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Codeforces 助手")
        
        self.context = AppContext()
        
        try: self.root.geometry(self.context.config_mgr.data.get("window_size", "950x650"))
        except: self.root.geometry("950x650")
        
        self.ui = MainWindow(self.root, self.context)
        
        self.context.on_ui_refresh_needed = lambda: self.root.after(0, self.ui.refresh_data_ui)

        self._start_loops()

    def _start_loops(self):
        def update_time():
            try: self.ui.canvas.itemconfig(self.ui.time_label_id, text=datetime.now().strftime("%Y-%m-%d\n%H:%M:%S"))
            except: pass
            self.root.after(1000, update_time)
            
        def auto_refresh():
            rate = max(2, int(self.context.config_mgr.data.get("refresh_rate", 60)))
            self.context.trigger_global_refresh()
            self.root.after(rate * 1000, auto_refresh)

        update_time()
        self.root.after(0, auto_refresh) 

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MainApplication()
    app.run()