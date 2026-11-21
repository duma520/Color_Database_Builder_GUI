import sqlite3
from functools import lru_cache
from typing import Optional, Tuple
import json
import os

class ColorDatabase:
    """颜色数据库管理类"""
    
    def __init__(self, db_path: str = "colors.db"):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """初始化数据库和表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 创建颜色表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS colors (
                    r SMALLINT NOT NULL,
                    g SMALLINT NOT NULL,
                    b SMALLINT NOT NULL,
                    name TEXT NOT NULL,
                    PRIMARY KEY (r, g, b)
                )
            """)
            # 创建索引加速查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rgb ON colors(r, g, b)
            """)
            conn.commit()
    
    def add_color(self, r: int, g: int, b: int, name: str):
        """添加颜色到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO colors (r, g, b, name) VALUES (?, ?, ?, ?)",
                (r, g, b, name)
            )
            conn.commit()
    
    def bulk_import_from_json(self, json_file: str):
        """从JSON文件批量导入颜色数据"""
        with open(json_file, 'r') as f:
            colors = json.load(f)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for rgb_str, name in colors.items():
                r, g, b = map(int, rgb_str.split(','))
                cursor.execute(
                    "INSERT OR REPLACE INTO colors (r, g, b, name) VALUES (?, ?, ?, ?)",
                    (r, g, b, name)
                )
            conn.commit()
    
    def find_color(self, r: int, g: int, b: int) -> Optional[str]:
        """根据RGB值查询颜色名称"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM colors WHERE r=? AND g=? AND b=? LIMIT 1",
                (r, g, b)
            )
            result = cursor.fetchone()
            return result[0] if result else None


class ColorLookup:
    """颜色查询插件主类"""
    
    def __init__(self, db_path: str = "colors.db"):
        self.db = ColorDatabase(db_path)
    
    @lru_cache(maxsize=2048)
    def get_color_name(self, r: int, g: int, b: int) -> str:
        """
        获取颜色名称（带缓存）
        
        参数:
            r: 红色分量 (0-999)
            g: 绿色分量 (0-999)
            b: 蓝色分量 (0-999)
            
        返回:
            颜色名称字符串，如果未找到则返回"Unknown"
        """
        if not (0 <= r <= 999 and 0 <= g <= 999 and 0 <= b <= 999):
            return "Invalid RGB value"
            
        name = self.db.find_color(r, g, b)
        return name if name else "Unknown"
    
    def add_color(self, r: int, g: int, b: int, name: str):
        """添加自定义颜色"""
        self.db.add_color(r, g, b, name)
        self.get_color_name.cache_clear()  # 清除缓存
    
    def import_from_json(self, json_file: str):
        """从JSON文件导入颜色数据"""
        self.db.bulk_import_from_json(json_file)
        self.get_color_name.cache_clear()  # 清除缓存


# 示例用法
if __name__ == "__main__":
    # 初始化插件
    plugin = ColorLookup()
    
    # 如果有JSON数据文件，可以这样导入
    # plugin.import_from_json("color_data.json")
    
    # 添加一些示例颜色
    plugin.add_color(255, 0, 0, "Bright Red")
    plugin.add_color(0, 255, 0, "Pure Green")
    plugin.add_color(0, 0, 255, "Deep Blue")
    plugin.add_color(999, 999, 999, "Max White")
    
    # 查询颜色
    print(plugin.get_color_name(255, 0, 0))  # 输出: Bright Red
    print(plugin.get_color_name(100, 100, 100))  # 输出: Unknown
    print(plugin.get_color_name(999, 999, 999))  # 输出: Max White
    
    # 测试缓存效果
    import time
    start = time.time()
    for _ in range(1000):
        plugin.get_color_name(255, 0, 0)
    print(f"1000次查询耗时: {time.time()-start:.4f}秒 (使用缓存)")