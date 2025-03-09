import os
import sqlite3
from datetime import datetime

def get_data_dir():
    """获取data目录路径"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

class DatabaseManager:
    def __init__(self, db_name=None):
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        
        # 从配置获取数据库名称
        self.db_path = os.path.join(data_dir, db_name) if db_name else os.path.join(data_dir, 'emby_playback.db')
        self.init_db()
    
    def init_db(self):
        """初始化数据库结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 播放历史表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS playback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    device_name TEXT,
                    client_type TEXT,
                    media_name TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration INTEGER,
                    location TEXT
                )
            ''')
            
            # 安全日志表（带自动迁移）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    user_id TEXT,
                    username TEXT,
                    trigger_ip TEXT,
                    active_sessions INTEGER,
                    action TEXT
                )
            ''')
            
            # 检查旧表结构
            try:
                cursor = conn.execute("PRAGMA table_info(security_log)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'username' not in columns:
                    conn.execute('ALTER TABLE security_log ADD COLUMN username TEXT')
            except sqlite3.OperationalError:
                pass
            
            conn.commit()

    def record_session_start(self, session_data):
        """记录播放开始"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO playback_history (
                    session_id, user_id, username, ip_address,
                    device_name, client_type, media_name, 
                    start_time, location
                ) VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                session_data['session_id'],
                session_data['user_id'],
                session_data['username'],
                session_data['ip'],
                session_data['device'],
                session_data['client'],
                session_data['media'],
                session_data['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                session_data.get('location', '未知位置')
            ))
            conn.commit()

    def record_session_end(self, session_id, end_time, duration):
        """记录播放结束"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE playback_history 
                SET end_time = ?, duration = ?
                WHERE session_id = ?
            ''', (
                end_time.strftime('%Y-%m-%d %H:%M:%S'),
                duration,
                session_id
            ))
            conn.commit()

    def log_security_event(self, log_data):
        """记录安全日志"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO security_log 
                (timestamp, user_id, username, trigger_ip, active_sessions, action)
                VALUES (?,?,?,?,?,?)
            ''', (
                log_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                log_data['user_id'],
                log_data['username'],
                log_data['trigger_ip'],
                log_data['active_sessions'],
                log_data['action']
            ))
            conn.commit()