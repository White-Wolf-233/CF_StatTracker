import os
import json
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image, ImageDraw
from datetime import datetime
from scraper_methods import CodeforcesSpider

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "user_config.json")
CACHE_FILE = os.path.join(BASE_DIR, "data_cache.json")
AVATAR_FILE = os.path.join(BASE_DIR, "avatar_cache.png")

class ConfigManager:
    def __init__(self):
        self.default_config = {
            "handle": "", "api_key": "", "api_secret": "",
            "refresh_rate": 60, "window_size": "950x650",
            "sidebar_color": "#2C3E50", "card_color": "#141414", "bg_image": "",
            "rating_n": 5, "contest_n": 5, "contest_filters": ["All"],
            "module_order": ["basic_info", "rating_change", "last_contest", "upcoming"],
            "module_visibility": {"basic_info": True, "rating_change": True, "last_contest": True, "upcoming": True},
            "font_header": "Microsoft YaHei", "size_header": 16, "color_header": "#FFFFFF",
            "font_title": "Microsoft YaHei", "size_title": 12, "color_title": "#4DA8DA",
            "font_content": "Arial", "size_content": 11, "color_content": "#E0E0E0"
        }
        self.data = self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    merged = self.default_config.copy()
                    merged.update(saved)
                    return merged
            except: pass
        return self.default_config.copy()

    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)


class AppState:
    """全局状态机"""
    def __init__(self):
        self.dashboard = {}
        self.wrong_list = []
        self.avatar_pil = None
        self.ac_count = "..."
        self.status_msg = "状态: 加载本地缓存..."
        self.status_is_err = False
        self.load_cache()

    def load_cache(self):
        """读取上次的缓存数据"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.dashboard = data.get("dashboard", {})
                    self.wrong_list = data.get("wrong_list", [])
                    self.ac_count = data.get("ac_count", "...")
            except: pass
            
        if os.path.exists(AVATAR_FILE):
            try: self.avatar_pil = Image.open(AVATAR_FILE).convert("RGBA")
            except: pass

    def save_cache(self):
        """存储缓存到本地"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({"dashboard": self.dashboard, "wrong_list": self.wrong_list, "ac_count": self.ac_count}, f, ensure_ascii=False)
        except: pass


class TaskExecutor:
    def __init__(self, max_workers=3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    def submit(self, func, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)


class CFDataService:
    def __init__(self, config_mgr: ConfigManager, state: AppState):
        self.config = config_mgr.data
        self.state = state
        self.spider = CodeforcesSpider(self.config.get("api_key", ""), self.config.get("api_secret", ""))
        self.fetch_lock = threading.Lock()

    def update_spider_auth(self):
        self.spider = CodeforcesSpider(self.config.get("api_key", ""), self.config.get("api_secret", ""))

    def fetch_all_dashboard_data(self):
        h = self.config.get("handle")
        if not h: raise ValueError("Handle is empty")
        basic_info = self.spider.get_user_info(h)
        if not basic_info:
            raise Exception("获取基础信息失败，网络异常或被拦截")
        new_data = {}
        new_data["basic_info"] = basic_info
        new_data["upcoming"] = self.spider.get_upcoming_contests(self.config.get("contest_n", 5), self.config.get("contest_filters", ["All"]))
        new_data["rating_change"] = self.spider.get_recent_rating_changes(h, self.config.get("rating_n", 5))
        new_data["last_contest"] = self.spider.get_time_since_last_contest(h)
        
        try:
            self.state.ac_count = self.spider.get_ac_count(h)
        except Exception:
            pass

        self.state.dashboard = new_data
        self.state.save_cache() # 获取成功后立即保存缓存
        
        # 同步静默下载头像并存入本地缓存
        if new_data["basic_info"] and new_data["basic_info"].get("titlePhoto"):
            self._download_avatar(new_data["basic_info"].get("titlePhoto"))

    def fetch_wrong_problems(self):
        h = self.config.get("handle")
        if not h: return
        wl = self.spider.get_wrong_problems(h, count=50)
        if wl is None:
            raise Exception("获取错题本失败，网络异常")
            
        self.state.wrong_list = wl
        self.state.save_cache()

    def _download_avatar(self, url):
        if not url or "no-avatar" in url: return
        if url.startswith("//"): url = "https:" + url
        try:
            resp = requests.get(url, timeout=5)
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            mask = Image.new('L', img.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0) + img.size, fill=255)
            img.putalpha(mask)
            self.state.avatar_pil = img.resize((80, 80), Image.Resampling.LANCZOS)
            self.state.avatar_pil.save(AVATAR_FILE, "PNG") # 保存头像图片到本地
        except: pass

    @staticmethod
    def check_contest_registration(contest_id):
        url = f"https://codeforces.com/contestRegistration/{contest_id}"
        resp = requests.get(url, allow_redirects=False, timeout=3)
        if resp.status_code == 302 and resp.headers.get('Location') == '/contests':
            return False, url
        return True, url


class BaseModule:
    key = ""
    default_name = ""
    def generate_lines(self, state, open_url_cb, check_reg_cb): raise NotImplementedError

class BasicInfoModule(BaseModule):
    key = "basic_info"
    default_name = "👤 账号基本信息"
    def generate_lines(self, state, open_url_cb, check_reg_cb):
        info = state.dashboard.get("basic_info")
        if not info: return [("数据拉取中...", None)]
        text = f"ID: {info.get('handle')} | 段位: {info.get('rank', 'Unrated').title()} | Rating: {info.get('rating', 'N/A')}"
        return [(text, lambda h=info.get('handle'): open_url_cb(f"https://codeforces.com/profile/{h}"))]

class RatingChangeModule(BaseModule):
    key = "rating_change"
    default_name = "📈 最近 Rating 变更记录"
    def generate_lines(self, state, open_url_cb, check_reg_cb):
        changes = state.dashboard.get("rating_change", [])
        if not changes: return [("暂无近期 Rating 变更", None)]
        return [
            (f"{'🟢 +' if (rc['newRating']-rc['oldRating'])>0 else '🔴 ' if (rc['newRating']-rc['oldRating'])<0 else '⚪ '}{rc['newRating']-rc['oldRating']} ({rc['oldRating']} ➔ {rc['newRating']}) | {rc['contestName']}", 
             lambda c_id=rc['contestId']: open_url_cb(f"https://codeforces.com/contest/{c_id}")) for rc in changes
        ]

class LastContestModule(BaseModule):
    key = "last_contest"
    default_name = "⏳ 距上次参赛时间"
    def generate_lines(self, state, open_url_cb, check_reg_cb):
        return [(f"距离上次参赛已过去: {state.dashboard.get('last_contest', '未知')}", None)]

class UpcomingModule(BaseModule):
    key = "upcoming"
    default_name = "📅 即将开始的竞赛"
    def generate_lines(self, state, open_url_cb, check_reg_cb):
        contests = state.dashboard.get("upcoming", [])
        if not contests: return [("近期无符合筛选条件的比赛", None)]
        return [
            (f"{i+1}. [{datetime.fromtimestamp(c['startTimeSeconds']).strftime('%m-%d %H:%M')}] {c['name']}", 
             lambda c_id=c['id']: check_reg_cb(c_id)) for i, c in enumerate(contests)
        ]

class ModuleRegistry:
    modules = [BasicInfoModule(), RatingChangeModule(), LastContestModule(), UpcomingModule()]
    module_dict = {m.key: m for m in modules}