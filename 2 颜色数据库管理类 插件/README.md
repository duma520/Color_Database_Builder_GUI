# 颜色查询插件 (ColorLookup Plugin) 全方位使用说明书

© 2025 杜玛 保留所有权利  
GitHub: [https://github.com/duma520](https://github.com/duma520)  
问题报告: 通过 GitHub Issues 提交  

---

## 目录
1. [简介](#简介)
2. [快速入门](#快速入门)
3. [核心功能详解](#核心功能详解)
4. [高级用法](#高级用法)
5. [应用场景举例](#应用场景举例)
6. [技术细节](#技术细节)
7. [版本更新记录](#版本更新记录)
8. [常见问题解答](#常见问题解答)
9. [版权与许可](#版权与许可)

---

## 简介

### 什么是颜色查询插件？
ColorLookup 是一个智能颜色管理工具，可以帮助您：
- 通过 RGB 值快速查找颜色名称
- 管理自定义颜色数据库
- 批量导入/导出颜色数据
- 查找相似颜色
- 进行 RGB 和 HEX 颜色代码转换

### 适用人群
- **普通用户**：想了解颜色名称的日常使用者
- **设计师**：需要精确管理颜色方案的专业人士
- **开发者**：需要在应用中集成颜色识别功能的程序员
- **数据分析师**：处理颜色相关数据的专业人士
- **教育工作者**：教授色彩理论的教师

### 主要特点
✔ 轻量级 SQLite 数据库存储  
✔ 高效的 LRU 缓存机制  
✔ 简单易用的 API 接口  
✔ 支持批量导入/导出  
✔ 跨平台兼容性  

---

## 快速入门

### 安装
```python
# 只需将 color_plugin.py 放入您的项目目录即可
from color_plugin import ColorLookup
```

### 基本使用
```python
# 初始化插件
color_finder = ColorLookup()

# 查询颜色名称
print(color_finder.get_color_name(255, 0, 0))  # 输出: Bright Red

# 添加自定义颜色
color_finder.add_color(128, 128, 128, "Medium Gray")

# 从JSON导入颜色
color_finder.import_from_json("my_colors.json")
```

---

## 核心功能详解

### 1. 颜色查询
```python
get_color_name(r, g, b) -> str
```
**参数**:
- `r`: 红色分量 (0-999)
- `g`: 绿色分量 (0-999)
- `b`: 蓝色分量 (0-999)

**返回值**: 颜色名称或 "Unknown"

**示例**:
```python
print(color_finder.get_color_name(0, 255, 0))  # 输出: Pure Green
```

### 2. 添加颜色
```python
add_color(r, g, b, name)
```
**用途**: 将自定义颜色添加到数据库

**示例**:
```python
color_finder.add_color(255, 192, 203, "Pink")
```

### 3. 批量导入
```python
import_from_json(json_file)
```
**JSON 格式要求**:
```json
{
    "r,g,b": "颜色名称",
    "255,0,0": "红色",
    "0,255,0": "绿色"
}
```

### 4. 相似颜色查找
```python
find_similar_color(r, g, b, threshold=50) -> list
```
**返回值**: 包含 (r,g,b,name,difference) 的列表

**示例**:
```python
similar = color_finder.find_similar_color(255, 100, 100, 30)
for r, g, b, name, diff in similar:
    print(f"{name}: 差异值 {diff}")
```

### 5. 颜色代码转换
```python
hex_to_rgb("#ff0000")  # 返回 (255, 0, 0)
rgb_to_hex(255, 0, 0)  # 返回 "#ff0000"
```

---

## 高级用法

### 自定义数据库路径
```python
# 使用自定义数据库文件
custom_db = ColorLookup("my_colors.db")
```

### 性能优化
- 自动缓存最近查询的2048个结果
- 手动清除缓存:
```python
color_finder.get_color_name.cache_clear()
```

### 数据库维护
直接操作 SQLite 数据库:
```sql
-- 查看所有颜色
SELECT * FROM colors ORDER BY name;

-- 删除颜色
DELETE FROM colors WHERE name = 'Old Color';
```

---

## 应用场景举例

### 1. 设计工作
设计师可以建立自己的颜色库，快速查询Pantone色号或自定义颜色名称。

### 2. 网站开发
```python
# 将用户上传的图片颜色转换为名称
dominant_color = (120, 80, 200)
color_name = color_finder.get_color_name(*dominant_color)
print(f"主色调: {color_name}")
```

### 3. 数据分析
分析产品图片颜色分布，统计最常出现的颜色名称。

### 4. 教育应用
```python
# 色彩学习工具
def quiz_color():
    r, g, b = random.randint(0,255), random.randint(0,255), random.randint(0,255)
    name = color_finder.get_color_name(r,g,b)
    print(f"RGB({r},{g},{b}) 是什么颜色？")
    # ...交互逻辑...
```

### 5. 物联网应用
通过RGB传感器检测环境颜色并获取标准名称。

---

## 技术细节

### 数据库结构
表 `colors` 结构:
- `r`: 红色分量 (SMALLINT)
- `g`: 绿色分量 (SMALLINT)
- `b`: 蓝色分量 (SMALLINT)
- `name`: 颜色名称 (TEXT)
- 主键: (r,g,b)

### 性能特点
- LRU缓存减少数据库查询
- 索引加速搜索
- 批量操作使用事务处理

### 算法说明
相似颜色计算使用曼哈顿距离:
```
差异值 = |r1-r2| + |g1-g2| + |b1-b2|
```

---

## 版本更新记录

### v1.0.0 (2025-01-01)
- 初始版本发布
- 基本颜色查询功能
- 数据库管理功能

### v1.1.0 (2025-03-15)
- 新增相似颜色查找功能
- 添加 HEX/RGB 转换方法
- 性能优化

### v1.2.0 (2025-05-01)
- 增强错误处理
- 改进文档
- 添加日志记录

---

## 常见问题解答

**Q: 为什么我的颜色查询返回 "Unknown"?**  
A: 表示该RGB值未在数据库中找到，请先使用add_color()添加。

**Q: RGB值范围为什么是0-999?**  
A: 设计为支持更广范围的颜色表示，但标准RGB仍是0-255。

**Q: 如何备份我的颜色数据库?**  
A: 直接复制.db文件即可，或导出为JSON格式。

**Q: 支持多线程吗?**  
A: 是，但建议每个线程使用独立的ColorLookup实例。

---

## 版权与许可

**版权所有 © 2025 杜玛**  
本软件及其文档受版权法保护，未经书面许可不得：
- 用于商业用途
- 修改后重新分发
- 移除版权信息

**允许**:
- 非商业用途的个人使用
- 教育用途
- 开源项目引用（需注明出处）

**声明**: 作者不提供私人邮箱支持，所有技术支持通过GitHub公开进行，以便其他用户也能受益。

---

**感谢您使用ColorLookup插件！**  
如有任何问题或建议，请通过GitHub Issues提交。  
项目地址: [https://github.com/duma520](https://github.com/duma520)
