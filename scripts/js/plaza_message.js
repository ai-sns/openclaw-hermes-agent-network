//plaza message

// 配置参数
const SLIDE_IN_DURATION = 850;      // ms, 滑入动画时间
const WAIT_BEFORE_NEXT = 2000;       // ms, 下条消息出现间隔
const MOVE_DURATION = 10000;         // ms, 完全向上滑完总时间（建议 > (SLIDE_IN_DURATION + WAIT_BEFORE_NEXT) * 消息数）
const TARGET_TOP = 30;              // px, 消息距离页面顶部的距离
const MAX_TEXT_LENGTH = 50;          // 最大文本长度

// 定义消息及其对应的URL
let messageData = [
    {text: "🎼 1-渐变滑入a", url: "https://www.baidu.com"},
    {text: "🍀 2-明快清新b", url: "https://www.google.com"},
    {text: "🌤️ 3-openai昨晚发布新一代模型，敬请期待。", url: "https://www.x.com"},
    {text: "🎉 4-无缝循环", url: "http://www.weibo.com"}
];

// 截断文本并在必要时添加省略号
function truncateText(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength - 3) + '...';
}

// 从网络获取数据
async function fetchMessageData() {
    try {
        const response = await fetch('http://www.ai-sns.org/news.json');
        const data = await response.json();

        // 使用 recommended 分类的内容，并添加 emoji
        messageData = data.recommended.map((item, index) => {
            const emojis = ["🎼", "🍀", "🌤️", "🎉", "🚀", "💡", "🌐", "🔥"];
            const emoji = emojis[index % emojis.length];
            const fullText = `${emoji} ${index + 1}-${item.title}`;
            return {
                text: truncateText(fullText, MAX_TEXT_LENGTH),
                url: item.url
            };
        });

        // 更新消息显示
        updateMessages();
    } catch (error) {
        console.error('获取消息数据失败:', error);
        // 出错时保留原始消息
    }
}

// 获取消息容器
const container = document.querySelector('.message-container');

function open_in_browser(url) {
    open_url(url);
}

// 动态加载消息并获取容器的边界矩形
let messages = [];

function updateMessages() {
    // 清空现有的消息元素
    container.innerHTML = '';

    // 根据最新的 messageData 创建消息元素
    messages = messageData.map(messageItem => {
        // 创建一个div元素来显示每条消息
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = messageItem.text;

        // 为每个消息添加点击事件
        messageDiv.addEventListener('click', () => {
            open_in_browser(messageItem.url); // 点击后弹出相应的URL
        });

        // 将消息元素添加到消息容器中
        container.appendChild(messageDiv);

        return messageDiv; // 返回创建的消息元素
    });
}

// 获取消息容器的边界矩形
const containerRect = container.getBoundingClientRect();

let idx = 0;

// 计算消息滑动的目标距离（页面顶部30px）
function getTargetY() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const containerTop = container.getBoundingClientRect().top + scrollTop;
    return TARGET_TOP - containerTop;
}

// 为每个消息生成唯一滑动动画（使多条消息可同时向上动）
function slideMessage(msg) {
    // 起始位置
    msg.style.opacity = '1';
    msg.style.pointerEvents = 'auto';
    msg.style.zIndex = 2;

    // 动画前先清除transform，保证位置准确
    msg.style.transition = 'none';
    msg.style.transform = 'translateY(60px) scale(0.96)';

    // 触发回流以保证transition生效
    void msg.offsetWidth;

    // 滑入阶段（0.55s）
    msg.style.transition = `transform ${SLIDE_IN_DURATION}ms cubic-bezier(.62,1.78,.56,1.1), opacity ${SLIDE_IN_DURATION}ms`;
    msg.style.transform = 'translateY(0) scale(1)';
    msg.style.opacity = '1';

    // 等待滑入结束后，切换为持续上移（不隐藏）
    setTimeout(() => {
        // 计算目标Y（到达页面顶部30px）
        const targetY = getTargetY();

        // 持续上移，并逐渐淡出
        msg.style.transition = `transform ${MOVE_DURATION}ms linear, opacity 600ms ${MOVE_DURATION - 600}ms`;
        msg.style.transform = `translateY(${targetY}px) scale(0.98)`;
        msg.style.opacity = '0';

        // 到顶端并隐去后彻底隐藏，释放z-index
        setTimeout(() => {
            msg.style.transition = 'none';
            msg.style.opacity = '0';
            msg.style.zIndex = 1;
        }, MOVE_DURATION);

    }, SLIDE_IN_DURATION);
}

var timeout_id = null;

function play_plaza_message() {
    // 启动当前消息动画
    if (messages.length > 0) {
        slideMessage(messages[idx]);

        // 下条消息在WAIT_BEFORE_NEXT后出现
        idx = (idx + 1) % messages.length;
        timeout_id = setTimeout(play_plaza_message, SLIDE_IN_DURATION + WAIT_BEFORE_NEXT);
    }
}

// 页面加载完成后获取网络数据
document.addEventListener('DOMContentLoaded', () => {
    fetchMessageData();
});

// 窗口缩放需重新计算动画终点
window.addEventListener('resize', () => {
    // 对正在滑动的消息重新定位终点
    messages.forEach(msg => {
        const style = window.getComputedStyle(msg);
        if (style.opacity !== "0" && style.transform !== "none") {
            const matrix = new DOMMatrixReadOnly(style.transform);
            if (matrix.m42 !== 0 && matrix.m42 !== 60) { // 已经在上滑
                const targetY = getTargetY();
                msg.style.transition = ''; // 清除过渡, 立即定位
                msg.style.transform = `translateY(${targetY}px) scale(0.98)`;
            }
        }
    });
});

// 停止消息轮播的函数
function stop_plaza_message() {
    // 清除所有未执行的setTimeout
        if(timeout_id) {
            window.clearTimeout(timeout_id);
        }else{return true}

    // 重置所有消息的样式
    messages.forEach(msg => {
        msg.style.transition = 'none';
        msg.style.opacity = '0';
        msg.style.transform = 'translateY(60px) scale(0.96)';
        msg.style.pointerEvents = 'none';
        msg.style.zIndex = 1;
    });
}
