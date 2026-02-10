import json
import time
import random
import os
import hashlib
from datetime import datetime
import requests
import certifi
import urllib3
from requests.exceptions import SSLError, Timeout, ConnectionError, RequestException
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

DEMO_CODES = ["DEMO-CODE-001", "DEMO-CODE-002"]

def send_demo_code(token, user_id):
    headers = dict(DEMO_HEADERS)
    headers['Authorization'] = f'DEMO {token}'
    
    for code in DEMO_CODES:
        try:
            redeem_url = f"https://demo.example.com:8080/demo_redeem/{code}"
            resp = demo_get(redeem_url, headers=headers, timeout=5, max_retries=2)
        except Exception:
            pass

def build_log_key(value):
    if not value:
        return None
    return "log_" + hashlib.md5(str(value).encode('utf-8')).hexdigest()

def fast_extract_int(text, key):
    if not text:
        return None
    needle = f"\"{key}\""
    idx = text.find(needle)
    if idx == -1:
        return None
    idx = text.find(":", idx)
    if idx == -1:
        return None
    i = idx + 1
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    sign = 1
    if i < len(text) and text[i] == "-":
        sign = -1
        i += 1
    num = 0
    start = i
    while i < len(text) and text[i].isdigit():
        num = num * 10 + (ord(text[i]) - 48)
        i += 1
    if i == start:
        return None
    return sign * num

def demo_request_with_retry(request_func, url, max_retries=3, retry_delay=2, backoff_factor=2, **kwargs):
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return request_func(url, **kwargs)
        except (Timeout, ConnectionError, SSLError, RequestException) as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = retry_delay * (backoff_factor ** attempt)
                time.sleep(wait_time)
            else:
                raise last_exception
        except Exception as e:
            raise e
    
    raise last_exception

def demo_post(url, **kwargs):
    max_retries = kwargs.pop('max_retries', 3)
    retry_delay = kwargs.pop('retry_delay', 2)
    
    def post_func(url, **kwargs):
        kwargs.setdefault('verify', certifi.where())
        kwargs.setdefault('timeout', (10, 30))
        kwargs.setdefault('proxies', {"http": None, "https": None})
        return requests.post(url, **kwargs)
    
    return demo_request_with_retry(post_func, url, max_retries=max_retries, retry_delay=retry_delay, **kwargs)

def demo_get(url, **kwargs):
    max_retries = kwargs.pop('max_retries', 3)
    retry_delay = kwargs.pop('retry_delay', 2)
    
    def get_func(url, **kwargs):
        kwargs.setdefault('verify', certifi.where())
        kwargs.setdefault('timeout', (10, 30))
        kwargs.setdefault('proxies', {"http": None, "https": None})
        return requests.get(url, **kwargs)
    
    return demo_request_with_retry(get_func, url, max_retries=max_retries, retry_delay=retry_delay, **kwargs)

def demo_put(url, **kwargs):
    max_retries = kwargs.pop('max_retries', 3)
    retry_delay = kwargs.pop('retry_delay', 2)
    
    def put_func(url, **kwargs):
        kwargs.setdefault('verify', certifi.where())
        kwargs.setdefault('timeout', (10, 30))
        kwargs.setdefault('proxies', {"http": None, "https": None})
        return requests.put(url, **kwargs)
    
    return demo_request_with_retry(put_func, url, max_retries=max_retries, retry_delay=retry_delay, **kwargs)

def demo_delete(url, **kwargs):
    max_retries = kwargs.pop('max_retries', 3)
    retry_delay = kwargs.pop('retry_delay', 2)
    
    def delete_func(url, **kwargs):
        kwargs.setdefault('verify', certifi.where())
        kwargs.setdefault('timeout', (10, 30))
        kwargs.setdefault('proxies', {"http": None, "https": None})
        return requests.delete(url, **kwargs)
    
    return demo_request_with_retry(delete_func, url, max_retries=max_retries, retry_delay=retry_delay, **kwargs)

DEMO_VERSION = "Demo-1.0.0"
DEMO_HEADERS = {
    'Host': 'demo.example.com:8080',
    'Accept': 'application/json',
    'X-Demo-Key': f'demo-xxxxxx:Demo {DEMO_VERSION}',
    'Demo-Api-Key': f'demo-xxxxxx:Demo {DEMO_VERSION}',
    'Content-Type': 'application/json',
    'User-Agent': f'demo/{DEMO_VERSION} Windows/10.0'
}

def generate_random_hash():
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(32))

class SimpleLogger:
    def __init__(self):
        self.log_file = "demo_log.txt"
        self.logs_dir = "demo_logs"
        
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')

class DemoModeManager:
    def __init__(self, config_file="demo_config.json"):
        self.config_file = config_file
        self.logger = SimpleLogger()
        self.load_config()
    
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
        self.config.setdefault('pick_count', 10)
        self.config.setdefault('pick_delay_min', 1)
        self.config.setdefault('pick_delay_max', 3)
        self.config.setdefault('games_per_session', 3)
        self.config.setdefault('match_timeout', 180)
        self.config.setdefault('delay_between_matches', 30)
        self.config.setdefault('max_session_runs', 0)
        self.config.setdefault('skip_turns', 1)
        self.config.setdefault('turn_wait_timeout', 30)
        self.config.setdefault('end_match_timeout', 10)
        self.config.setdefault('max_retries', 3)
        self.config.setdefault('retry_delay', 2)
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.log(f"保存失败: {e}")
    
    def create_demo_account(self):
        try:
            deviceid = time.time()
            devicepassword = time.time()
            random_hash = generate_random_hash()
            
            loginjson = {
                "provider": "demo_id",
                "provider_details": {"payment_provider": "DEMO"},
                "client_type": "DEMO",
                "build": f"Demo {DEMO_VERSION}",
                "platform_type": "Windows",
                "app_guid": "DemoApp",
                "version": f"Demo {DEMO_VERSION}",
                "platform_info": f'{{"device_profile": "Windows", "hash": "{random_hash}", "locale": "zh-CN"}}',
                "platform_version": "Windows",
                "language": "zh-Hans",
                "automatic_account_creation": True,
                "username": f"demo:Windows-{deviceid}",
                "password": f"{devicepassword}"
            }
            
            time.sleep(random.uniform(0.1, 0.3))
            create = demo_post('https://demo.example.com:8080/demo_session', 
                              headers=DEMO_HEADERS, 
                              json=loginjson,
                              timeout=30,
                              max_retries=self.config.get('max_retries', 3))
            
            if not create.ok:
                if create.status_code == 429:
                    time.sleep(10)
                    return {'success': False, 'error': "频率限制"}
                return {'success': False, 'error': f"HTTP {create.status_code}"}
            
            create_data = create.json()
            DEMO_TOKEN = create_data.get('demo_token')
            pid = create_data.get('user_id')
            
            if not DEMO_TOKEN or not pid:
                return {'success': False, 'error': "未获取到令牌"}

            headers_auth = dict(DEMO_HEADERS)
            headers_auth['Authorization'] = f'DEMO {DEMO_TOKEN}'
            name = f"DemoUser{random.randint(100, 999)}"
            
            time.sleep(0.1)
            demo_put(f'https://demo.example.com:8080/demo_users/{pid}', 
                     headers=headers_auth, 
                     json={"action": "set-name", "value": f"{name}"},
                     max_retries=self.config.get('max_retries', 3))
            
            account_info = {
                'username': f"demo:Windows-{deviceid}",
                'password': f"{devicepassword}",
                'demo_token': DEMO_TOKEN,
                'pid': pid,
                'display_name': name,
                'log_key': build_log_key(f"demo:Windows-{deviceid}"),
                'total_sessions': 0,
                'total_games': 0,
                'total_wins': 0,
                'current_session_games': 0,
                'current_session_round': 0,
                'current_game_in_round': 0,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': '正常',
                'has_draft': False,
                'last_draft_time': None
            }
            time.sleep(2)
            send_demo_code(DEMO_TOKEN, pid)
            self.config['accounts'].append(account_info)
            
            with open("demo_accounts.txt", "a") as file:
                file.write(f"demo:Windows-{deviceid}|{devicepassword}|{name}\n")
            
            self.save_config()
            return {'success': True, 'account': account_info}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def login_demo_account(self, account):
        try:
            random_hash = generate_random_hash()
            platform_info = f'{{"device_profile": "Windows", "hash": "{random_hash}", "locale": "zh-CN"}}'

            login_data = {
                "provider": "demo_id",
                "provider_details": {"payment_provider": "DEMO"},
                "client_type": "DEMO",
                "build": f"Demo {DEMO_VERSION}",
                "platform_type": "Windows",
                "app_guid": "DemoApp",
                "version": f"Demo {DEMO_VERSION}",
                "platform_info": platform_info,
                "platform_version": "Windows",
                "language": "zh-Hans",
                "automatic_account_creation": False,
                "username": account['username'],
                "password": account['password']
            }
            
            login = demo_post('https://demo.example.com:8080/demo_session',
                             headers=DEMO_HEADERS,
                             json=login_data,
                             timeout=30,
                             max_retries=self.config.get('max_retries', 3))
            
            if login.status_code == 403:
                account['status'] = '异常'
                self.logger.log("账号异常")
                return False
            
            if not login.ok:
                if login.status_code == 429:
                    self.logger.log("频率限制")
                    time.sleep(15)
                    return False
                self.logger.log(f"登录失败: {login.status_code}")
                return False
            
            login_json = login.json()
            DEMO_TOKEN = login_json.get('demo_token')
            if not DEMO_TOKEN:
                self.logger.log("未获取到令牌")
                return False
            
            headers_auth = dict(DEMO_HEADERS)
            headers_auth['Authorization'] = f'DEMO {DEMO_TOKEN}'
            account['headers'] = headers_auth
            account['demo_token'] = DEMO_TOKEN
            
            pid = login_json.get('user_id')
            account['pid'] = pid
            account['status'] = '正常'
            
            self.logger.log("登录成功")
            return True
                
        except Exception as e:
            self.logger.log(f"登录异常: {str(e)}")
            return False
    
    def buy_demo_ticket(self, account):
        try:
            pid = account.get('pid')
            headers = account.get('headers')
            
            draft_url = f"https://demo.example.com:8080/demo_draft/{pid}"
            resp = demo_post(draft_url, headers=headers, timeout=30,
                           max_retries=self.config.get('max_retries', 3))
        
            if resp.ok:
                account['has_draft'] = False
                account['last_draft_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True
            else:
                self.logger.log(f"购买失败: {resp.status_code}")
                return False
        
        except Exception as e:
            self.logger.log(f"购买异常: {str(e)}")
            return False
    
    def pick_demo_cards(self, account):
        try:
            pid = account.get('pid')
            headers = account.get('headers')
            pick_count = self.config.get('pick_count', 10)
            delay_min = self.config.get('pick_delay_min', 1)
            delay_max = self.config.get('pick_delay_max', 3)
            
            self.logger.log(f"尝试选卡，共{pick_count}次")
            
            has_selected = False
            
            for i in range(pick_count):
                try:
                    get_resp = demo_get(f"https://demo.example.com:8080/demo_draft/{pid}/deck", 
                                      headers=headers, timeout=30,
                                      max_retries=self.config.get('max_retries', 3))
                    
                    if get_resp.status_code == 403:
                        self.logger.log("遇到403，跳过选卡")
                        if has_selected:
                            account['has_draft'] = True
                        return True
                    
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)
                    
                    pick_num = random.randint(0, 2)
                    
                    pick_resp = demo_put(
                        f"https://demo.example.com:8080/demo_draft/{pid}/deck",
                        headers=headers,
                        json={"pick": pick_num},
                        timeout=30,
                        max_retries=self.config.get('max_retries', 3)
                    )
                    
                    if pick_resp.status_code == 403:
                        self.logger.log("提交遇到403，跳过选卡")
                        account['has_draft'] = True
                        return True
                    
                    if not pick_resp.ok:
                        self.logger.log(f"第{i+1}次选卡失败: {pick_resp.status_code}")
                    else:
                        has_selected = True
                    
                    self.logger.log(f"第{i+1}/{pick_count}次选卡完成")
                    
                except Exception as e:
                    self.logger.log(f"第{i+1}次选卡异常: {str(e)}")
            
            if has_selected:
                account['has_draft'] = True
            self.logger.log("选卡尝试完成")
            return True
            
        except Exception as e:
            self.logger.log(f"选卡过程异常: {str(e)}")
            return True
    
    def start_demo_match(self, account):
        try:
            pid = account.get('pid')
            headers = account.get('headers')
            
            lobby_resp = demo_post(
                'https://demo.example.com:8080/demo_lobby',
                headers=headers,
                json={
                    "user_id": pid,
                    "deck_id": 0,
                    "extra_data": "demo:"
                },
                timeout=30,
                max_retries=self.config.get('max_retries', 3)
            )
            
            if lobby_resp.status_code == 403:
                account['status'] = '异常'
                self.logger.log("账号异常")
                return False
            
            if not lobby_resp.ok:
                self.logger.log(f"开始失败: {lobby_resp.status_code}")
                return False
            
            self.logger.log("匹配请求已发送")
            return True
            
        except Exception as e:
            self.logger.log(f"开始异常: {str(e)}")
            return False
    
    def wait_for_demo_match(self, account):
        try:
            pid = account.get('pid')
            headers = account.get('headers')
            timeout = self.config.get('match_timeout', 180)
            
            self.logger.log(f"等待匹配，超时{timeout}秒...")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                matches_resp = demo_get(
                    'https://demo.example.com:8080/demo_matches',
                    headers=headers,
                    timeout=30,
                    max_retries=self.config.get('max_retries', 3)
                )
                
                if matches_resp and matches_resp.ok:
                    if matches_resp.text.strip() not in ["null", "null\n"]:
                        try:
                            res = json.loads(matches_resp.text)
                            matchdata = res.get('demo_match_data', {})
                            current_match = matchdata.get('match', {}) if isinstance(matchdata, dict) else {}
                            match_id = current_match.get('match_id')
                            if match_id:
                                own_side = current_match.get('action_side')
                                if not own_side:
                                    own_side = "left"
                                
                                self.logger.log(f"匹配成功！比赛ID: {match_id}, 位置: {own_side}")
                                return {"match_id": match_id, "own_side": own_side, "pid": pid}
                        except:
                            pass
                
                time.sleep(2)
            
            self.logger.log("匹配超时")
            return None
            
        except Exception as e:
            self.logger.log(f"等待异常: {str(e)}")
            return None
    
    def play_demo_game(self, account):
        try:
            match_info = self.wait_for_demo_match(account)
            if not match_info:
                self.logger.log("未能匹配到对手")
                return False
            
            match_id = match_info['match_id']
            own_side = match_info['own_side']
            pid = match_info['pid']
            headers = account.get('headers')
            
            self.logger.log(f"开始比赛 {match_id}")
            
            action_url = f"https://demo.example.com:8080/demo_matches/{match_id}/actions"
            next_action_id = 1
            
            try:
                demo_post(action_url, headers=headers, json={
                    "action_id": next_action_id,
                    "action_type": "DemoStart",
                    "user_id": pid,
                    "action_data": {"userID": pid}
                }, timeout=30, max_retries=self.config.get('max_retries', 3))
                next_action_id += 1
                time.sleep(0.5)
            except:
                pass
            
            skip_turns = self.config.get('skip_turns', 1)
            
            self.logger.log(f"开始跳过前{skip_turns}回合")
            
            for turn_index in range(skip_turns):
                for check in range(20):
                    try:
                        matches_resp = demo_get('https://demo.example.com:8080/demo_matches',
                                               headers=headers, timeout=30,
                                               max_retries=self.config.get('max_retries', 3))
                        if matches_resp and matches_resp.ok:
                            res = json.loads(matches_resp.text)
                            matchdata = res.get('demo_match_data', {})
                            current_match = matchdata.get('match', {}) if isinstance(matchdata, dict) else {}
                            action_side = current_match.get('action_side')
                            if action_side == own_side:
                                break
                    except:
                        pass
                    time.sleep(2)
                
                try:
                    demo_post(action_url, headers=headers, json={
                        "action_id": next_action_id,
                        "action_type": "DemoTurnStart",
                        "user_id": pid,
                        "action_data": {"side": f"{own_side}"}
                    }, timeout=30, max_retries=self.config.get('max_retries', 3))
                    next_action_id += 1
                except:
                    pass
                
                time.sleep(0.5)
                
                try:
                    demo_post(action_url, headers=headers, json={
                        "action_id": next_action_id,
                        "action_type": "DemoTurnEnd",
                        "user_id": pid,
                        "action_data": {"side": f"{own_side}"}
                    }, timeout=30, max_retries=self.config.get('max_retries', 3))
                    next_action_id += 1
                except:
                    pass
                
                self.logger.log(f"已跳过第{turn_index+1}回合")
                time.sleep(2)
            
            self.logger.log("跳过回合完成，结束比赛")
            
            end_data = {
                "side": "",
                "action": "end-demo-match",
                "value": {
                    "winner_id": pid,
                    "winner_side": own_side,
                    "result": "Demo_Victory"
                }
            }
            
            end_url = f"https://demo.example.com:8080/demo_matches/{match_id}"
            end_timeout = self.config.get('end_match_timeout', 10)
            
            try:
                end_resp = demo_put(end_url, headers=headers, json=end_data, timeout=end_timeout,
                                  max_retries=self.config.get('max_retries', 3))
                if end_resp and end_resp.ok:
                    self.logger.log("比赛结束成功")
                    return True
                else:
                    self.logger.log(f"结束失败: {end_resp.status_code if end_resp else '无响应'}")
            except Exception as e:
                self.logger.log(f"结束异常: {str(e)}")
            
            return False
            
        except Exception as e:
            self.logger.log(f"进行比赛异常: {str(e)}")
            return False
    
    def claim_demo_reward(self, account):
        try:
            pid = account.get('pid')
            headers = account.get('headers')
            
            draft_url = f"https://demo.example.com:8080/demo_draft/{pid}"
            reward_resp = demo_delete(draft_url, headers=headers, timeout=30,
                                     max_retries=self.config.get('max_retries', 3))
            
            if reward_resp.status_code == 403:
                account['status'] = '异常'
                self.logger.log("账号异常")
                return False
            
            if not reward_resp.ok:
                self.logger.log(f"领取失败: {reward_resp.status_code}")
                return False
            
            self.logger.log("奖励领取成功")
            account['has_draft'] = False
            return True
            
        except Exception as e:
            self.logger.log(f"领取异常: {str(e)}")
            return False
    
    def run_demo_cycle(self, account):
        try:
            current_session_round = account.get('current_session_round', 0) + 1
            account['current_session_round'] = current_session_round
            account['current_game_in_round'] = 0
            account['current_session_games'] = 0
            
            self.logger.log(f"开始第 {current_session_round} 次演示")
            
            if account.get('has_draft', False):
                self.logger.log("已有演示卡组，跳过购买和选卡")
            else:
                if not self.buy_demo_ticket(account):
                    return False
                time.sleep(2)
                
                self.pick_demo_cards(account)
                time.sleep(2)
            
            games_per_session = self.config.get('games_per_session', 3)
            self.logger.log(f"开始演示比赛，目标{games_per_session}局")
            
            for game_num in range(games_per_session):
                account['current_game_in_round'] = game_num + 1
                account['current_session_games'] = game_num + 1
                
                self.logger.log(f"第{game_num+1}/{games_per_session}局比赛")
                
                if not self.start_demo_match(account):
                    self.logger.log("开始比赛失败")
                    break
                
                time.sleep(2)
                
                if self.play_demo_game(account):
                    account['total_games'] = account.get('total_games', 0) + 1
                    account['total_wins'] = account.get('total_wins', 0) + 1
                    
                    if game_num < games_per_session - 1:
                        delay = self.config.get('delay_between_matches', 30)
                        random_delay = random.uniform(delay * 0.8, delay * 1.2)
                        self.logger.log(f"等待{random_delay:.1f}秒后继续")
                        time.sleep(random_delay)
                else:
                    self.logger.log("比赛失败")
                    break
            
            completed_games = account.get('current_session_games', 0)
            if completed_games >= games_per_session:
                self.logger.log(f"演示完成{completed_games}局，开始领取奖励")
                if self.claim_demo_reward(account):
                    account['total_sessions'] = account.get('total_sessions', 0) + 1
                    account['current_game_in_round'] = 0
                    account['current_session_games'] = 0
                    self.save_config()
                    self.logger.log(f"演示周期完成！总次数: {account['total_sessions']}")
                    return True
                else:
                    self.logger.log("领取奖励失败")
                    return False
            else:
                self.logger.log(f"只完成了{completed_games}/{games_per_session}局")
                self.save_config()
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"运行演示周期异常: {str(e)}")
            return False
    
    def demo_mode(self):
        accounts = self.config['accounts']
        if not accounts:
            self.logger.log("没有账号")
            return
        
        if len(accounts) == 1:
            account = accounts[0]
        else:
            self.logger.log(f"发现 {len(accounts)} 个账号")
            for i, acc in enumerate(accounts):
                name = acc.get('display_name', acc.get('username', '未知'))
                status = acc.get('status', '正常')
                has_draft = acc.get('has_draft', False)
                draft_status = "有卡组" if has_draft else "无卡组"
                current_round = acc.get('current_session_round', 0)
                current_game = acc.get('current_game_in_round', 0)
                total_games = acc.get('current_session_games', 0)
                progress = f"第{current_round}次演示第{current_game}局" if current_game > 0 else "未开始"
                self.logger.log(f"{i+1}. {name} - 状态: {status}, 卡组: {draft_status}, 进度: {progress}, 当前演示局数: {total_games}")
            
            try:
                choice = int(input("选择账号: "))
                if choice < 1 or choice > len(accounts):
                    self.logger.log("序号无效")
                    return
                account = accounts[choice-1]
            except:
                self.logger.log("输入无效")
                return
        
        if account.get('status') == '异常':
            self.logger.log("账号异常，无法使用")
            return
        
        if not self.login_demo_account(account):
            self.logger.log("登录失败，无法继续")
            return
        
        current_round = account.get('current_session_round', 0)
        current_game = account.get('current_game_in_round', 0)
        total_games = account.get('current_session_games', 0)
        if current_game > 0:
            self.logger.log(f"发现上次进度: 第{current_round}次演示的第{current_game}局")
            resume = input("是否继续？(y/n): ").strip().lower()
            if resume != 'y':
                account['current_session_round'] = 0
                account['current_game_in_round'] = 0
                account['current_session_games'] = 0
        
        max_runs = self.config.get('max_session_runs', 0)
        runs_done = account.get('total_sessions', 0)
        
        self.logger.log(f"开始演示模式")
        if max_runs > 0:
            self.logger.log(f"最大演示次数: {max_runs}")
        
        try:
            while True:
                if max_runs > 0 and runs_done >= max_runs:
                    self.logger.log(f"已完成 {max_runs} 次演示")
                    break
                
                self.logger.log(f"开始第 {runs_done + 1} 次演示")
                if self.run_demo_cycle(account):
                    runs_done = account.get('total_sessions', 0)
                    
                    current_game = account.get('current_game_in_round', 0)
                    if current_game == 0:
                        if max_runs > 0:
                            self.logger.log(f"进度: {runs_done}/{max_runs}次演示")
                        
                        delay = 30
                        self.logger.log(f"等待{delay}秒后继续")
                        time.sleep(delay)
                    else:
                        self.logger.log(f"继续当前演示，进度: 第{current_game}局")
                        time.sleep(10)
                else:
                    self.logger.log("演示周期失败，等待60秒后重试")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            self.logger.log("用户中断")
        finally:
            total_runs = account.get('total_sessions', 0)
            total_games = account.get('total_games', 0)
            total_wins = account.get('total_wins', 0)
            has_draft = account.get('has_draft', False)
            draft_status = "有卡组" if has_draft else "无卡组"
            current_round = account.get('current_session_round', 0)
            current_game = account.get('current_game_in_round', 0)
            progress = f"第{current_round}次演示的第{current_game}局" if current_game > 0 else "未开始"
            
            self.logger.log(f"运行结束。总演示次数: {total_runs}, 总对局: {total_games}, 胜利: {total_wins}")
            self.logger.log(f"当前卡组: {draft_status}, 当前进度: {progress}")
            self.save_config()

def main():
    print('演示模式工具')
    
    manager = DemoModeManager()
    
    while True:
        print("\n" + "="*50)
        print("1. 创建演示账号")
        print("2. 配置演示设置")
        print("3. 开始演示模式")
        print("4. 查看账号")
        print("5. 清除卡组标记")
        print("6. 重置演示进度")
        print("0. 退出")
        print("="*50)
        
        choice = input("选择: ").strip()
        
        if choice == "1":
            result = manager.create_demo_account()
            if result['success']:
                print(f"创建成功: {result['account']['display_name']}")
            else:
                print(f"创建失败: {result.get('error', '未知错误')}")
        
        elif choice == "2":
            print("\n配置演示设置")
            try:
                pick_count = int(input(f"选卡次数 (默认10): ") or "10")
                if pick_count > 0:
                    manager.config['pick_count'] = pick_count
                
                games_per_session = int(input(f"每个演示打多少局 (默认3): ") or "3")
                if games_per_session > 0:
                    manager.config['games_per_session'] = games_per_session
                
                skip_turns = int(input(f"跳过回合数 (默认1): ") or "1")
                if skip_turns >= 0:
                    manager.config['skip_turns'] = skip_turns
                
                match_delay = int(input(f"对局间隔 (秒, 默认5): ") or "5")
                if match_delay > 0:
                    manager.config['delay_between_matches'] = match_delay
                
                max_runs = int(input(f"最大演示次数 (0=无限制): ") or "0")
                if max_runs >= 0:
                    manager.config['max_session_runs'] = max_runs
                
                match_timeout = int(input(f"匹配超时时间 (秒, 默认180): ") or "180")
                if match_timeout > 0:
                    manager.config['match_timeout'] = match_timeout
                
                max_retries = int(input(f"最大重试次数 (默认3): ") or "3")
                if max_retries >= 0:
                    manager.config['max_retries'] = max_retries
                
                retry_delay = int(input(f"重试延迟 (秒, 默认2): ") or "2")
                if retry_delay > 0:
                    manager.config['retry_delay'] = retry_delay
                
                manager.save_config()
                print("演示配置已保存")
            except ValueError:
                print("输入无效")
        
        elif choice == "3":
            manager.demo_mode()
        
        elif choice == "4":
            accounts = manager.config['accounts']
            if not accounts:
                print("没有账号")
            else:
                print(f"\n账号总数: {len(accounts)}")
                for i, acc in enumerate(accounts):
                    name = acc.get('display_name', acc.get('username', '未知'))
                    status = acc.get('status', '正常')
                    sessions = acc.get('total_sessions', 0)
                    total_games = acc.get('total_games', 0)
                    wins = acc.get('total_wins', 0)
                    has_draft = acc.get('has_draft', False)
                    draft_status = "有卡组" if has_draft else "无卡组"
                    last_draft = acc.get('last_draft_time', '从未')
                    current_round = acc.get('current_session_round', 0)
                    current_game = acc.get('current_game_in_round', 0)
                    total_current_games = acc.get('current_session_games', 0)
                    progress = f"第{current_round}次演示的第{current_game}局" if current_game > 0 else "未开始"
                    print(f"{i+1}. {name}")
                    print(f"   状态: {status}, 演示次数: {sessions}, 总对局: {total_games}, 胜利: {wins}")
                    print(f"   卡组状态: {draft_status}, 上次选卡: {last_draft}")
                    print(f"   当前进度: {progress}")
        
        elif choice == "5":
            accounts = manager.config['accounts']
            if not accounts:
                print("没有账号")
            else:
                print(f"\n选择要清除卡组标记的账号:")
                for i, acc in enumerate(accounts):
                    name = acc.get('display_name', acc.get('username', '未知'))
                    has_draft = acc.get('has_draft', False)
                    draft_status = "有卡组" if has_draft else "无卡组"
                    print(f"{i+1}. {name} - 当前: {draft_status}")
                
                try:
                    acc_choice = int(input("选择账号: "))
                    if 1 <= acc_choice <= len(accounts):
                        account = accounts[acc_choice-1]
                        account['has_draft'] = False
                        account['last_draft_time'] = None
                        manager.save_config()
                        print(f"已清除 {account['display_name']} 的卡组标记")
                    else:
                        print("序号无效")
                except:
                    print("输入无效")
        
        elif choice == "6":
            accounts = manager.config['accounts']
            if not accounts:
                print("没有账号")
            else:
                print(f"\n选择要重置演示进度的账号:")
                for i, acc in enumerate(accounts):
                    name = acc.get('display_name', acc.get('username', '未知'))
                    current_round = acc.get('current_session_round', 0)
                    current_game = acc.get('current_game_in_round', 0)
                    progress = f"第{current_round}次演示的第{current_game}局" if current_game > 0 else "未开始"
                    print(f"{i+1}. {name} - 当前进度: {progress}")
                
                try:
                    acc_choice = int(input("选择账号: "))
                    if 1 <= acc_choice <= len(accounts):
                        account = accounts[acc_choice-1]
                        account['current_session_round'] = 0
                        account['current_game_in_round'] = 0
                        account['current_session_games'] = 0
                        account['has_draft'] = False
                        manager.save_config()
                        print(f"已重置 {account['display_name']} 的演示进度")
                    else:
                        print("序号无效")
                except:
                    print("输入无效")
        
        elif choice == "0":
            print("退出")
            break

if __name__ == "__main__":
    main()