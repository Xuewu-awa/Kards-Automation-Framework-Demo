import requests
import json
import sys
import certifi
import time
import random
import urllib3
import threading
import os
import queue
import string
import warnings
from datetime import datetime
from requests.exceptions import SSLError
from urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import deque

urllib3.disable_warnings()

class AdvancedLogger:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.log_file = "log.txt"
        self.screen_logs = {}
        self.full_logs = {}
        self.display_lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.terminal_width = 80
        self.running = True
        self.update_terminal_size()
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"日志开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
    
    def update_terminal_size(self):
        try:
            self.terminal_width = os.get_terminal_size().columns
        except:
            self.terminal_width = 80
    
    def add_player(self, player_name):
        if player_name not in self.screen_logs:
            self.screen_logs[player_name] = "等待开始..."
            self.full_logs[player_name] = deque(maxlen=100)
    
    def remove_player(self, player_name):
        if player_name in self.screen_logs:
            del self.screen_logs[player_name]
            del self.full_logs[player_name]
    
    def format_screen_log(self, player_name, message):
        short_name = player_name[:10] if len(player_name) > 10 else player_name
        short_name = f"{short_name:10s}"
        timestamp = datetime.now().strftime("%H:%M:%S")
        max_msg_len = self.terminal_width - 25
        if len(message) > max_msg_len:
            message = message[:max_msg_len-3] + "..."
        return f"[{short_name}] [{timestamp}] {message}"
    
    def format_file_log(self, player_name, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{player_name}] {message}"
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{'='*self.terminal_width}")
        print(f"演示工具".center(self.terminal_width))
        print(f"{'='*self.terminal_width}")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"运行状态: {'运行中' if self.running else '已停止'}")
        print(f"{'-'*self.terminal_width}")
    
    def update_display(self):
        with self.display_lock:
            self.clear_screen()
            sorted_players = sorted(self.screen_logs.keys())
            for player in sorted_players:
                log_line = self.screen_logs[player]
                print(log_line)
            print(f"\n{'-'*self.terminal_width}")
            print(f"活跃玩家: {len(self.screen_logs)} 个 | 按 Ctrl+C 停止")
            print(f"{'='*self.terminal_width}")
    
    def log_to_screen(self, player_name, message):
        if player_name not in self.screen_logs:
            self.add_player(player_name)
        screen_message = self.format_screen_log(player_name, message)
        self.screen_logs[player_name] = screen_message
        self.update_display()
    
    def log_to_file(self, player_name, message):
        file_message = self.format_file_log(player_name, message)
        with self.file_lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(file_message + '\n')
    
    def log(self, player_name, message):
        self.log_to_screen(player_name, message)
        self.log_to_file(player_name, message)
        if player_name in self.full_logs:
            self.full_logs[player_name].append(message)
    
    def stop(self):
        self.running = False
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"日志结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")

class RequestLimiter:
    def __init__(self):
        self.last_request_time = 0
        self.min_delay = 0.5
        self.max_delay = 2.0
        self.lock = threading.Lock()
        self.account_requests = {}
        self.request_counts = {}
        
    def wait_for_account(self, account_id=None):
        current_time = time.time()
        with self.lock:
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last + random.uniform(0.1, 0.3)
                time.sleep(wait_time)
            
            if account_id:
                last_account_time = self.account_requests.get(account_id, 0)
                time_since_account = current_time - last_account_time
                if time_since_account < 1.0:
                    wait_time = 1.0 - time_since_account + random.uniform(0.1, 0.3)
                    time.sleep(wait_time)
                self.account_requests[account_id] = time.time()
                
                self.request_counts[account_id] = self.request_counts.get(account_id, 0) + 1
                
                if self.request_counts[account_id] % 50 == 0:
                    extra_wait = random.uniform(2.0, 5.0)
                    time.sleep(extra_wait)
            
            self.last_request_time = time.time()
            time.sleep(random.uniform(0.1, 0.3))

request_limiter = RequestLimiter()

class ThreadSafeHTTPClient:
    def __init__(self, account_id=None, player_name=None):
        self.account_id = account_id
        self.player_name = player_name
        self.session = None
        self.headers = None
        self.init_session()
        
    def init_session(self):
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=2,
            pool_maxsize=2,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.headers = {
            'Host': 'demo.example.com:8080',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'X-Demo-Key': 'demo-xxxxxxxxx:Demo 1.0.0',
            'Demo-Api-Key': 'demo-xxxxxxxxx:Demo 1.0.0',
            'Content-Type': 'application/json',
            'User-Agent': f'demo/1.0.0 Windows/10.0 Thread-{threading.get_ident()}'
        }
        
        self.session.headers.update(self.headers)
    
    def set_jwt_token(self, jwt_token):
        if jwt_token:
            self.headers['Authorization'] = f'DEMO {jwt_token}'
            self.session.headers.update(self.headers)
    
    def clear_jwt_token(self):
        if 'Authorization' in self.headers:
            del self.headers['Authorization']
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def safe_request(self, method, url, **kwargs):
        try:
            request_limiter.wait_for_account(self.account_id)
            
            kwargs.setdefault('timeout', (10, 60))
            kwargs.setdefault('verify', certifi.where())
            
            response = self.session.request(method, url, **kwargs)
            
            try:
                response.content
            except Exception as e:
                if self.player_name:
                    print(f"[{self.player_name}] 读取响应内容失败: {str(e)}")
                response = requests.Response()
                response.status_code = 500
                response._content = b'{"error": "Response read failed"}'
                
            return response
            
        except SSLError:
            warnings.simplefilter('ignore', InsecureRequestWarning)
            kwargs['verify'] = False
            return self.session.request(method, url, **kwargs)
            
        except Exception as e:
            if self.player_name:
                print(f"[{self.player_name}] 请求异常: {str(e)}")
            raise
    
    def post(self, url, **kwargs):
        return self.safe_request('POST', url, **kwargs)
    
    def get(self, url, **kwargs):
        return self.safe_request('GET', url, **kwargs)
    
    def put(self, url, **kwargs):
        return self.safe_request('PUT', url, **kwargs)

def generate_random_hash():
    characters = string.ascii_lowercase + string.digits
    length = random.randint(16, 32)
    return ''.join(random.choice(characters) for _ in range(length))

class AccountManager:
    def __init__(self, config_file="demo_config.json"):
        self.config_file = config_file
        self.load_config()
        self.lock = threading.Lock()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}
        self.config.setdefault('accounts', [])
        self.config.setdefault('max_concurrent_creation', 3)
        self.config.setdefault('match_duration_seconds', 180)
        self.config.setdefault('delay_between_matches', 30)
        self.config.setdefault('max_matches_per_account', 0)
        self.config.setdefault('max_concurrent_accounts', 5)
        self.config.setdefault('game_mode', 'normal')
        
    def save_config(self):
        try:
            with self.lock:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def create_single_account(self):
        try:
            http_client = ThreadSafeHTTPClient()
            
            deviceid = time.time()
            devicepassword = time.time()
            random_hash = generate_random_hash()
            
            loginjson = {
                "provider": "demo_id",
                "provider_details": {"payment_provider": "DEMO"},
                "client_type": "DEMO",
                "build": "Demo 1.0.0",
                "platform_type": "Windows",
                "app_guid": "DemoApp",
                "version": "Demo 1.0.0",
                "platform_info": f'{{"device_profile": "Windows", "hash": "{random_hash}", "locale": "zh-CN"}}',
                "platform_version": "Windows",
                "language": "zh-Hans",
                "automatic_account_creation": True,
                "username": f"demo:Windows-{deviceid}",
                "password": f"{devicepassword}"
            }
            
            create = http_client.post('https://demo.example.com:8080/demo_session', json=loginjson)
            
            if not create.ok:
                if create.status_code == 429:
                    time.sleep(10)
                    return {'success': False, 'error': "频率限制"}
                return {'success': False, 'error': f"HTTP {create.status_code}"}
            
            create_data = create.json()
            DEMO_TOKEN = create_data.get('demo_token')
            pid = create_data.get('player_id')
            
            if not DEMO_TOKEN:
                return {'success': False, 'error': "未获取到令牌"}
            
            http_client.set_jwt_token(DEMO_TOKEN)
            name = f"DemoUser {random.randint(1000, 9999)}"
            
            time.sleep(0.5)
            http_client.put(f'https://demo.example.com:8080/demo_players/{pid}', 
                          json={"action":"set-name","value":f"{name}"})
            
            account_info = {
                'username': f"demo:Windows-{deviceid}",
                'password': f"{devicepassword}",
                'jwt': DEMO_TOKEN,
                'pid': pid,
                'display_name': name,
                'total_matches': 0,
                'wins': 0,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': '正常',
                'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with self.lock:
                self.config['accounts'].append(account_info)
            
            with open("demo_accounts.txt", "a") as file:
                file.write(f"demo:Windows-{deviceid}|{devicepassword}|{name}\n")
            
            return {'success': True, 'account': account_info}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class AccountWorker(threading.Thread):
    def __init__(self, account, config, logger, stop_event):
        threading.Thread.__init__(self)
        self.account = account
        self.config = config
        self.logger = logger
        self.stop_event = stop_event
        self.daemon = True
        
        self.player_name = account.get('display_name', account.get('username', 'DemoUser'))
        self.http_client = ThreadSafeHTTPClient(
            account_id=account.get('pid'),
            player_name=self.player_name
        )
        
        self.matches_done = 0
        self.wins = 0
        self.losses = 0
        self.last_match_time = 0
        self.last_login_time = 0
        self.login_refresh_count = 0
        self.banned = False
        self.banned_reason = ""
        self.consecutive_failures = 0
        self.demo_token = None
        self.pid = account.get('pid')
        
        self.game_mode = config.get('game_mode', 'normal')
        self.match_duration = config.get('match_duration_seconds', 180)
    
    def log(self, message):
        self.logger.log(self.player_name, message)
    
    def login_account(self):
        try:
            if self.banned:
                self.log("账号异常")
                return False
            
            current_time = time.time()
            
            self.http_client.clear_jwt_token()
            self.demo_token = None
            
            login_data = {
                "provider": "demo_id",
                "provider_details": {"payment_provider": "DEMO"},
                "client_type": "DEMO",
                "build": "Demo 1.0.0",
                "platform_type": "Windows",
                "app_guid": "DemoApp",
                "version": "Demo 1.0.0",
                "platform_info": '{"device_profile": "Windows", "locale": "zh-CN"}',
                "platform_version": "Windows",
                "language": "zh-Hans",
                "automatic_account_creation": False,
                "username": self.account['username'],
                "password": self.account['password']
            }
            
            self.log("登录中...")
            login = self.http_client.post('https://demo.example.com:8080/demo_session', json=login_data)
            
            self.log(f"登录状态: {login.status_code}")
            
            if login.status_code == 403:
                self.log("账号异常")
                self.banned = True
                self.banned_reason = "403错误"
                self.account['status'] = '异常'
                return False
            
            if not login.ok:
                if login.status_code == 429:
                    self.log("频率限制")
                    time.sleep(15)
                    return False
                if login.text and ('error' in login.text.lower()):
                    self.log("账号异常")
                    self.banned = True
                    self.banned_reason = "返回错误"
                    self.account['status'] = '异常'
                    return False
                self.log(f"登录失败: {login.status_code}")
                return False
            
            try:
                login_json = login.json()
            except:
                self.log("响应格式错误")
                return False
            
            DEMO_TOKEN = login_json.get('demo_token')
            if not DEMO_TOKEN:
                self.log("无令牌")
                return False
            
            self.demo_token = DEMO_TOKEN
            self.http_client.set_jwt_token(DEMO_TOKEN)
            
            self.account['jwt'] = DEMO_TOKEN
            self.account['pid'] = login_json.get('player_id')
            self.account['status'] = '正常'
            self.account['last_check'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.pid = self.account['pid']
            self.http_client.account_id = self.pid
            
            self.log("登录成功")
            self.last_login_time = time.time()
            self.last_match_time = time.time()
            self.login_refresh_count += 1
            return True
                
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False
    
    def run_one_match(self):
        try:
            if self.banned:
                self.log("账号异常")
                return False
            
            if not self.demo_token or not self.pid:
                self.log("未登录")
                if not self.login_account():
                    return False
            
            self.log("清理状态")
            time.sleep(1)
            
            self.log("获取卡组")
            time.sleep(random.uniform(0.5, 1.0))
            decks_resp = self.http_client.get(f'https://demo.example.com:8080/demo_players/{self.pid}/demo_decks')
            
            if decks_resp.status_code == 403:
                self.log("账号异常")
                self.banned = True
                self.banned_reason = "403错误"
                self.account['status'] = '异常'
                return False
            
            if not decks_resp.ok:
                if decks_resp.status_code == 429:
                    self.log("频率限制")
                    time.sleep(10)
                    return False
                self.log(f"获取失败: {decks_resp.status_code}")
                return False
            
            try:
                decks_data = decks_resp.json()
            except:
                self.log("响应格式错误")
                return False
            
            if isinstance(decks_data, dict) and 'demo_decks' in decks_data:
                decks = decks_data.get('demo_decks', [])
            elif isinstance(decks_data, list):
                decks = decks_data
            else:
                decks = []
            
            self.log(f"卡组数: {len(decks)}")
            if not decks:
                self.log("无卡组")
                return False
            
            deck_id = decks[0].get('id')
            self.log(f"使用卡组: {deck_id}")
            time.sleep(random.uniform(1.0, 2.0))
            
            self.log("创建比赛")
            create_resp = self.http_client.post('https://demo.example.com:8080/demo_lobby', 
                                              json={"player_id": self.pid, "deck_id": deck_id})
            
            if create_resp.status_code == 403:
                self.log("账号异常")
                self.banned = True
                self.banned_reason = "403错误"
                self.account['status'] = '异常'
                return False
            
            if not create_resp.ok:
                if create_resp.status_code == 429:
                    self.log("频率限制")
                    time.sleep(15)
                    return False
                self.log(f"创建失败: {create_resp.status_code}")
                return False
            
            wait_time = random.uniform(8.0, 12.0)
            self.log(f"匹配中 ({wait_time:.1f}秒)")
            time.sleep(wait_time)
            
            match_id = f"demo_match_{random.randint(10000, 99999)}"
            opponent_id = f"demo_ai_{random.randint(1000, 9999)}"
            
            self.log(f"比赛开始: {match_id}")
            
            start_time = time.time()
            last_log_time = start_time
            
            while time.time() - start_time < self.match_duration:
                if self.stop_event.is_set():
                    self.log("已停止")
                    return False
                
                current_time = time.time()
                elapsed = current_time - start_time
                
                if current_time - last_log_time >= 30:
                    remaining = (self.match_duration - elapsed)
                    self.log(f"进行中... {elapsed:.0f}秒")
                    last_log_time = current_time
                
                time.sleep(1)
            
            self.log("比赛结束")
            
            try:
                self.log("发送结束请求")
                time.sleep(random.uniform(1.0, 2.0))
                
                end_data = {
                    "side": "",
                    "action": "end-demo-match",
                    "value": {
                        "result": "demo_complete"
                    }
                }
                
                end_url = f"https://demo.example.com:8080/demo_matches/{match_id}"
                end_resp = self.http_client.put(end_url, json=end_data)
                self.log(f"结束状态: {end_resp.status_code}")
                
                if end_resp.ok:
                    return True
                else:
                    self.log(f"结束失败: {end_resp.status_code}")
                    return False
                    
            except Exception as e:
                self.log(f"结束异常: {str(e)}")
                return False
                
        except Exception as e:
            self.log(f"比赛异常: {str(e)}")
            return False
    
    def run(self):
        max_matches = self.config.get('max_matches_per_account', 0)
        self.matches_done = 0
        self.consecutive_failures = 0
        
        self.log(f"线程启动")
        
        if not self.login_account():
            self.log("登录失败")
            return
        
        while not self.stop_event.is_set():
            if self.login_refresh_count == 0 or self.matches_done % 20 == 0 or time.time() - self.last_login_time > 1200:
                self.log("刷新登录")
                if not self.login_account():
                    self.log("登录失败")
                    break
            
            if max_matches > 0 and self.matches_done >= max_matches:
                self.log(f"达到上限")
                break
            
            self.log(f"开始第 {self.matches_done + 1} 场比赛")
            if self.run_one_match():
                self.matches_done += 1
                self.consecutive_failures = 0
                
                if max_matches > 0:
                    self.log(f"进度: {self.matches_done}/{max_matches}")
                
                base_delay = self.config.get('delay_between_matches', 30)
                random_delay = random.uniform(base_delay * 0.8, base_delay * 1.2)
                self.log(f"等待 {random_delay:.1f} 秒")
                
                delay_start = time.time()
                while time.time() - delay_start < random_delay:
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
            else:
                if self.banned:
                    self.log("账号异常")
                    break
                
                self.consecutive_failures += 1
                
                if self.consecutive_failures <= 2:
                    wait_time = random.uniform(10, 20)
                elif self.consecutive_failures <= 5:
                    wait_time = random.uniform(20, 40)
                else:
                    wait_time = random.uniform(40, 60)
                    self.log("多次失败")
                    if not self.login_account():
                        break
                
                self.log(f"失败，等待 {wait_time:.1f} 秒")
                
                fail_start = time.time()
                while time.time() - fail_start < wait_time:
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        if self.http_client and self.http_client.session:
            self.http_client.session.close()
        
        total = self.wins + self.losses
        if total > 0:
            win_rate = (self.wins / total) * 100
            self.log(f"结束。总计: {total} 场")
        else:
            self.log("结束")

class DemoMultiApp:
    def __init__(self):
        self.manager = AccountManager()
        self.stop_event = threading.Event()
        self.worker_threads = []
        self.logger = AdvancedLogger()
    
    def configure_settings(self):
        print("\n" + "="*80)
        print("配置设置")
        print("="*80)
        
        print("\n选择模式:")
        print("1. 普通模式")
        print("2. 自定义模式")
        
        mode_choice = input("选择 (1/2): ").strip()
        if mode_choice == '2':
            self.manager.config['game_mode'] = 'custom'
            try:
                duration = int(input("每场时长 (秒): "))
                if duration > 0:
                    self.manager.config['match_duration_seconds'] = duration
            except:
                pass
        else:
            self.manager.config['game_mode'] = 'normal'
        
        try:
            delay = int(input("间隔时间 (秒): "))
            if delay > 0:
                self.manager.config['delay_between_matches'] = delay
        except:
            pass
        
        try:
            concurrent = int(input("最大并发数: "))
            if concurrent > 0:
                self.manager.config['max_concurrent_accounts'] = concurrent
        except:
            pass
        
        self.manager.save_config()
        
        mode_text = "普通模式" if self.manager.config['game_mode'] == 'normal' else "自定义模式"
        print(f"\n配置完成:")
        print(f"模式: {mode_text}")
        print(f"时长: {self.manager.config.get('match_duration_seconds', 180)} 秒")
        print(f"间隔: {self.manager.config.get('delay_between_matches', 30)} 秒")
        print(f"并发: {self.manager.config.get('max_concurrent_accounts', 5)} 个")
    
    def start_app(self):
        if self.worker_threads:
            print("已在运行")
            return
        accounts = self.manager.config['accounts']
        if not accounts:
            print("请先添加账号")
            return
        print("启动中...")
        normal_accounts = [acc for acc in accounts if acc.get('status') != '异常']
        if not normal_accounts:
            print("无可用账号")
            return
        self.stop_event.clear()
        max_concurrent = self.manager.config.get('max_concurrent_accounts', 5)
        accounts_to_process = normal_accounts[:max_concurrent]
        
        print(f"\n启动 {len(accounts_to_process)} 个:")
        for i, account in enumerate(accounts_to_process):
            print(f"  {i+1}. {account.get('display_name', account.get('username'))}")
        
        for account in accounts_to_process:
            worker = AccountWorker(
                account=account,
                config=self.manager.config,
                logger=self.logger,
                stop_event=self.stop_event
            )
            self.worker_threads.append(worker)
            worker.start()
            time.sleep(0.3)
        
        print(f"\n已启动，{len(accounts_to_process)} 个同时运行")
        print("按 Ctrl+C 停止")
    
    def stop_app(self):
        if not self.worker_threads:
            print("未运行")
            return
        print("停止中...")
        self.stop_event.set()
        for worker in self.worker_threads:
            worker.join(timeout=5)
        self.worker_threads.clear()
        self.manager.save_config()
        self.logger.stop()
        print("已停止")
    
    def view_accounts(self):
        accounts = self.manager.config['accounts']
        if not accounts:
            print("无账号")
            return
        
        print(f"\n账号总数: {len(accounts)}")
        print(f"{'-'*80}")
        print(f"{'序号':<5} {'账号名':<15} {'状态':<10} {'总场次':<8} {'创建时间':<19}")
        print(f"{'-'*80}")
        
        for i, acc in enumerate(accounts, 1):
            status = acc.get('status', '正常')
            total_matches = acc.get('total_matches', 0)
            created = acc.get('created_at', '未知')
            name = acc.get('display_name', acc.get('username', '未知'))
            
            print(f"{i:<5} {name:<15} {status:<10} {total_matches:<8} {created:<19}")
        
        normal_count = sum(1 for acc in accounts if acc.get('status') != '异常')
        banned_count = len(accounts) - normal_count
        print(f"{'-'*80}")
        print(f"正常 {normal_count} | 异常 {banned_count}")
    
    def interactive_menu(self):
        print("\n" + "="*80)
        print("演示工具")
        print("="*80)
        
        while True:
            accounts = self.manager.config['accounts']
            print(f"\n账号: {len(accounts)}")
            normal_accounts = [acc for acc in accounts if acc.get('status') != '异常']
            print(f"正常: {len(normal_accounts)}")
            print("\n1. 创建账号")
            print("2. 配置设置")
            print("3. 开始运行")
            print("4. 停止运行")
            print("5. 查看账号")
            print("0. 退出")
            print("="*80)
            
            choice = input("选择: ").strip()
            
            if choice == "1":
                try:
                    amount = int(input("创建数量: "))
                    if amount <= 0:
                        print("无效数量")
                        continue
                    success = 0
                    for i in range(amount):
                        result = self.manager.create_single_account()
                        if result['success']:
                            success += 1
                            print(f"成功: {result['account']['display_name']}")
                        else:
    