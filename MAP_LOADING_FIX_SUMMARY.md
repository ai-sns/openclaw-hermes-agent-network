# 地图动态加载问题修复总结

## 问题描述
用户发现即使数据库中map_type设置为'0'（Google Map），系统仍然加载map.html（百度地图）而不是googlemap3d.html。

## 根本原因
系统中有**多处硬编码**的map.html引用，之前只修改了Electron主进程中的map window，但SNS页面中的iframe地图加载没有修改。

## 修复的文件

### 1. renderer/js/modules/sns/snsHandlers.js (第463行)
**问题**: SNS页面的iframe直接硬编码加载map.html
**修复**:
- 将`loadBaiduMap()`改为`async loadBaiduMap()`
- 添加API调用获取地图配置
- 根据map_type动态设置iframe.src

```javascript
// 修复前
iframe.src = 'http://localhost:8788/scripts/map.html';

// 修复后
let mapUrl = 'http://localhost:8788/scripts/map.html';
const response = await fetch('http://localhost:8788/api/sns/map-config');
const result = await response.json();
if (result.success && result.data) {
    const mapType = String(result.data.map_type).trim();
    if (mapType === '0') {
        mapUrl = 'http://localhost:8788/scripts/googlemap3d.html';
    }
}
iframe.src = mapUrl;
```

### 2. renderer/js/pages.js (第1632行)
**问题**: 另一个地图加载函数也硬编码了map.html
**修复**: 同样的修改逻辑

### 3. electron/main.js (第118行)
**问题**: Map window硬编码加载map.html
**修复**: 已在之前修复，添加了动态加载逻辑

## 调试日志
修复后，浏览器控制台会显示：
```
加载地图
Map config API response: {success: true, data: {...}}
Map type: 0
Loading Google Map
Final map URL: http://localhost:8788/scripts/googlemap3d.html
地图页面加载完成
```

## 测试步骤
1. 确保API服务器运行: `python api_server.py`
2. 确认数据库map_type为'0':
   ```bash
   python3 -c "import sqlite3; conn = sqlite3.connect('db/db.sqlite'); cursor = conn.cursor(); cursor.execute('SELECT map_type FROM aichat_cfg LIMIT 1'); print(cursor.fetchone()); conn.close()"
   ```
3. 刷新Electron应用或重启
4. 打开浏览器开发者工具查看控制台日志
5. 应该看到加载googlemap3d.html的日志

## 关键点
- **SNS页面的地图是通过iframe加载的**，不是独立的map window
- 用户看到的是SNS页面中嵌入的iframe地图
- 必须修改renderer/js中的loadBaiduMap函数，而不仅仅是electron/main.js

## 其他硬编码位置（已确认不影响）
以下位置也有map.html引用，但都是注释或备份文件，不影响实际运行：
- ui/ui_*.py (PyQt版本，已废弃)
- backend/modules/sns/ai_social_engine.py (后端引擎，独立逻辑)
- MessageBoxEarth.py (旧版本)

## 验证方法
1. 打开Electron应用
2. 进入SNS页面
3. 按F12打开开发者工具
4. 查看Console标签
5. 应该看到"Loading Google Map"和正确的URL
6. 在Network标签中应该看到请求googlemap3d.html而不是map.html
