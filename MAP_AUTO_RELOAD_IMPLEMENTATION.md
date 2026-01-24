# 地图配置保存后自动重新加载实现

## 功能描述
在地图配置对话框中保存配置后，如果地图类型发生变化，系统会自动重新加载地图，无需重启应用。

## 实现方案

### 1. SNSMapConfigDialog.js 修改

#### 添加原始地图类型存储
```javascript
constructor() {
    this.dialog = null;
    this.originalMapType = null; // 存储原始地图类型
}
```

#### 加载配置时保存原始值
```javascript
async loadMapConfig() {
    // ...
    this.originalMapType = data.map_type; // 保存原始地图类型
    // ...
}
```

#### 保存后检查并触发重新加载
```javascript
async saveConfiguration() {
    // ... 保存逻辑 ...

    if (result.success) {
        alert('地图配置保存成功！');

        // 检查地图类型是否改变
        if (this.originalMapType !== mapType) {
            console.log('Map type changed - reloading map');
            this.reloadMap();
        }

        this.dialog.remove();
    }
}
```

#### 添加重新加载方法
```javascript
reloadMap() {
    // 移除现有的iframe
    const mapContainer = document.getElementById('mapContainer');
    if (mapContainer) {
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            existingIframe.remove();
            console.log('Removed existing map iframe');
        }

        // 触发自定义事件通知重新加载
        window.dispatchEvent(new CustomEvent('reloadMap'));
    }
}
```

### 2. snsHandlers.js 修改

#### 初始化时添加监听器
```javascript
init() {
    // ... 其他初始化 ...
    this.initMapReloadListener();
}
```

#### 添加重新加载监听器
```javascript
initMapReloadListener() {
    window.addEventListener('reloadMap', () => {
        console.log('Received reloadMap event - reloading map');
        this.loadBaiduMap();
    });
}
```

## 工作流程

1. **用户打开地图配置对话框**
   - 加载当前配置
   - 保存原始的 `map_type` 值

2. **用户修改地图类型并保存**
   - 发送配置到后端
   - 后端保存到数据库

3. **前端检查地图类型是否改变**
   - 比较 `originalMapType` 和新的 `mapType`
   - 如果不同，触发重新加载

4. **重新加载地图**
   - 移除现有的 iframe
   - 触发 `reloadMap` 自定义事件
   - snsHandlers 监听到事件
   - 调用 `loadBaiduMap()` 重新加载地图
   - `loadBaiduMap()` 会自动获取最新配置并加载正确的地图

## 优势

1. **即时生效** - 无需重启应用
2. **用户体验好** - 保存后立即看到新地图
3. **解耦设计** - 使用事件机制，组件间松耦合
4. **智能判断** - 只在地图类型改变时才重新加载

## 测试步骤

1. 打开应用，进入SNS页面
2. 当前显示百度地图（map.html）
3. 点击"地图配置"按钮
4. 选择 Google Map
5. 点击"保存"
6. 观察：
   - 弹出"地图配置保存成功！"
   - 控制台显示 "Map type changed from 1 to 0 - reloading map"
   - 控制台显示 "Removed existing map iframe"
   - 控制台显示 "Received reloadMap event - reloading map"
   - 地图自动切换为 Google Map（googlemap3d.html）

## 控制台日志示例

```
地图配置保存成功！
Map type changed from 1 to 0 - reloading map
Removed existing map iframe
Received reloadMap event - reloading map
加载地图
Map config API response: {success: true, data: {...}}
Map type: 0
Loading Google Map
Final map URL: http://localhost:8788/scripts/googlemap3d.html
地图页面加载完成
```

## 注意事项

1. 如果地图类型没有改变，不会触发重新加载
2. 重新加载会清除地图的当前状态（位置、缩放等）
3. 新地图会从数据库中加载保存的位置信息
