import os
import time
import sqlite3
from datetime import datetime
import requests

class EmbyMonitor:
    def __init__(self, db_manager, emby_client, security_client, config):
        self.db = db_manager
        self.emby = emby_client
        self.security = security_client
        self.config = config
        self.active_sessions = {}
        
        # 预处理白名单（不区分大小写）
        self.whitelist = [name.strip().lower() 
                         for name in config['security']['whitelist'] 
                         if name.strip()]
        
        # 安全配置
        self.auto_disable = config['security']['auto_disable']
        self.alert_threshold = config['notifications']['alert_threshold']
        self.alerts_enabled = config['notifications']['enable_alerts']

    def process_sessions(self):
        """核心会话处理逻辑"""
        try:
            current_sessions = self.emby.get_active_sessions()
            self._detect_new_sessions(current_sessions)
            self._detect_ended_sessions(current_sessions)
        except Exception as e:
            print(f"❌ 会话更新失败: {str(e)}")

    def _detect_new_sessions(self, current_sessions):
        """识别新会话"""
        for session_id, session in current_sessions.items():
            if session_id not in self.active_sessions:
                self._record_session_start(session)

    def _detect_ended_sessions(self, current_sessions):
        """识别结束会话"""
        ended = set(self.active_sessions.keys()) - set(current_sessions.keys())
        for sid in ended:
            self._record_session_end(sid)

    def _record_session_start(self, session):
        """记录新会话"""
        try:
            user_id = session['UserId']
            user_info = self.emby.get_user_info(user_id)
            ip_address = session.get('RemoteEndPoint', '').split(':')[0]
            username = user_info.get('Name', '未知用户').strip()

            # 白名单检查
            if username.lower() in self.whitelist:
                print(f"⚪ 白名单用户 [{username}] 跳过监控")
                return

            # 获取媒体信息
            media_item = session.get('NowPlayingItem', {})
            media_name = self.emby.parse_media_info(media_item)
            
            # 获取地理位置
            location = self._get_location(ip_address)

            session_data = {
                'session_id': session['Id'],
                'user_id': user_id,
                'username': username,
                'ip': ip_address,
                'device': session.get('DeviceName', '未知设备'),
                'client': session.get('Client', '未知客户端'),
                'media': media_name,
                'start_time': datetime.now(),
                'location': location
            }

            self.db.record_session_start(session_data)
            self.active_sessions[session['Id']] = session_data
            print(f"[▶] {username} | 设备: {session_data['device']} | IP: {ip_address} | 位置: {location} | 内容: {session_data['media']}")
            
            # 触发异常检测
            self._check_login_abnormality(user_id, ip_address)
        except KeyError as e:
            print(f"❌ 会话数据缺失关键字段: {str(e)}")
        except Exception as e:
            print(f"❌ 会话记录失败: {str(e)}")

    def _record_session_end(self, session_id):
        """记录会话结束"""
        try:
            session_data = self.active_sessions[session_id]
            end_time = datetime.now()
            duration = int((end_time - session_data['start_time']).total_seconds())
            
            self.db.record_session_end(session_id, end_time, duration)
            print(f"[■] {session_data['username']} | 时长: {duration//60}分{duration%60}秒")
            del self.active_sessions[session_id]
        except KeyError:
            print(f"⚠️ 会话 {session_id} 已不存在")
        except Exception as e:
            print(f"❌ 结束记录失败: {str(e)}")

    def _get_location(self, ip_address):
        """解析地理位置"""
        if not ip_address:
            return "未知位置"
        try:
            api_url = f"https://api.vore.top/api/IPdata?ip={ip_address}"
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 200 and 'ipdata' in data:
                    ipdata = data['ipdata']
                    loc_parts = []
                    if ipdata.get('info1'):
                        loc_parts.append(ipdata['info1'])
                    if ipdata.get('info2'):
                        loc_parts.append(ipdata['info2'])
                    if ipdata.get('info3'):
                        loc_parts.append(ipdata['info3'])
                    if loc_parts:
                        return ', '.join(loc_parts)
                    else:
                        return "未知区域"
                else:
                    return "未知区域"
            else:
                return "解析失败"
        except Exception as e:
            print(f"📍 解析 {ip_address} 失败: {str(e)}")
            return "解析失败"

    def _check_login_abnormality(self, user_id, new_ip):
        """检测登录异常"""
        if not self.alerts_enabled:
            return
        
        existing_ips = set()
        for sess in self.active_sessions.values():
            if sess['user_id'] == user_id and sess['ip'] != new_ip:
                existing_ips.add(sess['ip'])
        
        if len(existing_ips) >= (self.alert_threshold - 1):
            self._trigger_alert(user_id, new_ip, len(existing_ips)+1)

    def _trigger_alert(self, user_id, trigger_ip, session_count):
        """触发安全告警"""
        try:
            user_info = self.emby.get_user_info(user_id)
            username = user_info.get('Name', '未知用户').strip()
            
            # 最终白名单确认
            if username.lower() in self.whitelist:
                print(f"⚪ 白名单用户 [{username}] 受保护，跳过禁用")
                return

            location = self._get_location(trigger_ip)
            alert_msg = f"""
            🚨 安全告警 🚨
            时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            用户名: {username}
            可疑IP: {trigger_ip} ({location})
            并发会话数: {session_count}
            """
            print("=" * 60)
            print(alert_msg.strip())
            print("=" * 60)
            
            if self.auto_disable:
                if self.security.disable_user(user_id, username):
                    self._log_security_action(user_id, trigger_ip, session_count, username)
        except Exception as e:
            print(f"❌ 告警处理失败: {str(e)}")

    def _log_security_action(self, user_id, ip, count, username):
        """记录安全日志"""
        log_data = {
            'timestamp': datetime.now(),
            'user_id': user_id,
            'username': username,
            'trigger_ip': ip,
            'active_sessions': count,
            'action': 'DISABLE'
        }
        try:
            self.db.log_security_event(log_data)
        except Exception as e:
            print(f"❌ 安全日志记录失败: {str(e)}")

    def run(self):
        """启动监控服务"""
        print(f"🔍 监控服务启动 | 数据库: {self.config['database']['name']}")
        try:
            while True:
                self.process_sessions()
                time.sleep(self.config['monitor']['check_interval'])
        except KeyboardInterrupt:
            print("\n🛑 监控服务已安全停止")
        except Exception as e:
            print(f"❌ 监控服务异常终止: {str(e)}")