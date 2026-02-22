import time
import hashlib
import random
import logging
from datetime import datetime
import requests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CodeforcesSpider:
    def __init__(self, api_key: str, secret: str):
        self.api_key = api_key
        self.secret = secret
        self.base_url = "https://codeforces.com/api"

    def _generate_signature(self, method_name: str, params: dict) -> str:
        """生成 Codeforces API 要求的 SHA-512 授权签名"""
        rand_str = f"{random.randint(100000, 999999)}"
        sorted_params = sorted(params.items(), key=lambda x: (x[0], str(x[1])))
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        text_to_hash = f"{rand_str}/{method_name}?{query_string}#{self.secret}"
        hash_hex = hashlib.sha512(text_to_hash.encode('utf-8')).hexdigest()
        
        return f"{rand_str}{hash_hex}"

    def _request(self, method_name: str, params: dict = None) -> dict:
        if params is None:
            params = {}
            
        #鉴权
        params['apiKey'] = self.api_key
        params['time'] = int(time.time())
        params['apiSig'] = self._generate_signature(method_name, params)
        
        url = f"{self.base_url}/{method_name}"
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK":
                return data.get("result")
            else:
                logging.error(f"API 响应失败: {data.get('comment')}")
                return None
        except requests.RequestException as e:
            logging.error(f"网络异常: {e}")
            return None

    def get_user_info(self, handle: str) -> dict:
        """获取用户信息"""
        result = self._request("user.info", {"handles": handle})
        return result[0] if result else None

    def get_upcoming_contests(self, limit: int = 5, diff_filters: list = None) -> list:
        """获取即将开始的竞赛，支持数量限制和多个难度关键字筛选"""
        result = self._request("contest.list", {"gym": "false"})
        if not result:
            return []
            
        upcoming = [c for c in result if c.get("phase") == "BEFORE"]
        upcoming.sort(key=lambda x: x.get("startTimeSeconds", float('inf')))
        
        if diff_filters and "All" not in diff_filters and len(diff_filters) > 0:
            filtered_upcoming = []
            for c in upcoming:
                name = c.get('name', '').lower()
                # 只要比赛名称包含列表中任意一个选中的关键字，就保留
                if any(f.lower() in name for f in diff_filters):
                    filtered_upcoming.append(c)
            upcoming = filtered_upcoming
            
        return upcoming[:limit]

    def get_current_time(self) -> str:
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_recent_rating_changes(self, handle: str, count: int = 5) -> list:
        """获取最近 N 次 rating 变更"""
        result = self._request("user.rating", {"handle": handle})
        if result and len(result) > 0:
            # 截取最后 count 次比赛记录并反转（最近的在最前）
            return list(reversed(result[-count:]))
        return []

    def get_time_since_last_contest(self, handle: str) -> str:
        """计算距离上次参与计分竞赛的时间"""
        changes = self.get_recent_rating_changes(handle, count=1)
        
        if not changes or len(changes) == 0:
            return "无计分比赛记录"
            
        # 提取最近一次比赛的时间戳
        last_time = changes[0]['ratingUpdateTimeSeconds']
        diff_seconds = int(time.time()) - last_time
        days = diff_seconds // (24 * 3600)
        
        if days == 0:
            return "就在今天"
        return f"{days} 天前"

    def get_wrong_problems(self, handle: str, count: int = 100) -> list:
        """
        获取用户最近的错题（未通过的题目）
        :param handle: 用户名
        :param count: 向前追溯的提交记录数量（API 最大支持非常大的数字，但建议分批）
        """
        # 请求 user.status 接口，获取最新的 count 条提交记录
        result = self._request("user.status", {"handle": handle, "from": 1, "count": count})
        if not result:
            return []
            
        wrong_problems = []
        seen_problem_ids = set() #集合去重
        
        for submission in result:
            verdict = submission.get('verdict')
            problem = submission.get('problem')
            
            # 过滤掉已经通过的 (OK) 或者是还在评测中的 (TESTING)
            if verdict not in ['OK', 'TESTING']:
                # 拼接题目 ID (例如：比赛 1234 的 A 题 -> 1234A)
                problem_id = f"{problem.get('contestId', '')}{problem.get('index', '')}"
                if problem_id not in seen_problem_ids:
                    wrong_problems.append({
                        "id": problem_id,
                        "name": problem.get('name'),
                        "rating": problem.get('rating', 'Unrated'),
                        "tags": problem.get('tags', []),
                        "verdict": verdict
                    })
                    seen_problem_ids.add(problem_id)
                    
        return wrong_problems
    
    def get_ac_count(self, handle: str) -> int:
        """获取用户总 AC 题目数 (去重计算)"""
        # 不加 count 参数，默认获取该用户的所有提交历史
        result = self._request("user.status", {"handle": handle})
        if not result:
            return 0
            
        ac_problems = set()
        for submission in result:
            # 只统计 verdict 为 'OK' (即 Accepted) 的记录
            if submission.get('verdict') == 'OK':
                prob = submission.get('problem', {})
                # 拼接 比赛ID+题号 (如 1234A) 作为唯一标识
                prob_id = f"{prob.get('contestId', '')}{prob.get('index', '')}"
                ac_problems.add(prob_id)
                
        return len(ac_problems)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    API_KEY = ""
    API_SECRET = ""
    
    print("initializing")
    spider = CodeforcesSpider(api_key=API_KEY, secret=API_SECRET)
    test_handle = "Benq"
    print(f"tring to get {test_handle} rating")
    
    user_info = spider.get_user_info(test_handle)
    if user_info:
        print(f"successfully get {test_handle} rating: {user_info.get('rating')}")
    else:
        print("failure, check your API or net connection")
