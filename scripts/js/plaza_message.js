//plaza message

// Configuration parameters
const SLIDE_IN_DURATION = 850;      // ms, slide-in animation duration
const WAIT_BEFORE_NEXT = 2000;       // ms, interval before the next message appears
const MOVE_DURATION = 10000;         // ms, total time to slide fully upward (recommended > (SLIDE_IN_DURATION + WAIT_BEFORE_NEXT) * number of messages)
const TARGET_TOP = 30;              // px, distance from the top of the page
const MAX_TEXT_LENGTH = 50;          // max text length

// Define messages and their URLs
let messageData = [
    {text: "🎼 1-Gradient slide-in a", url: "https://www.baidu.com"},
    {text: "🍀 2-Bright and fresh b", url: "https://www.google.com"},
    {text: "🌤️ 3-OpenAI released a new generation model last night. Stay tuned.", url: "https://www.x.com"},
    {text: "🎉 4-Seamless loop", url: "http://www.weibo.com"}
];

// Truncate text and append ellipsis if needed
function truncateText(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength - 3) + '...';
}

// Fetch data from the network
async function fetchMessageData() {
    try {
        const resolvedBaseUrl = (typeof API_BASE_URL !== 'undefined' && API_BASE_URL)
            ? API_BASE_URL
            : ((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');
        const normalizedBaseUrl = (resolvedBaseUrl || '').replace(/\/+$/, '');
        const response = await fetch(`${normalizedBaseUrl}/api/get_news_list/`);
        const data = await response.json();

        // Use the 'recommended' category and add emojis
        messageData = data.recommended.map((item, index) => {
            const emojis = ["🎼", "🍀", "🌤️", "🎉", "🚀", "💡", "🌐", "🔥"];
            const emoji = emojis[index % emojis.length];
            const fullText = `${emoji} ${index + 1}-${item.title}`;
            return {
                text: truncateText(fullText, MAX_TEXT_LENGTH),
                url: item.url
            };
        });

        // Update message display
        updateMessages();
    } catch (error) {
        console.error('Failed to fetch message data:', error);
        // Keep the original messages on error
    }
}

// Get message container
const container = document.querySelector('.message-container');

function open_in_browser(url) {
    open_url(url);
}

// Dynamically load messages and get the container's bounding rect
let messages = [];

function updateMessages() {
    // Clear existing message elements
    container.innerHTML = '';

    // Create message elements based on the latest messageData
    messages = messageData.map(messageItem => {
        // Create a div element for each message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = messageItem.text;

        // Add click handler for each message
        messageDiv.addEventListener('click', () => {
            open_in_browser(messageItem.url); // Open the corresponding URL on click
        });

        // Append message element to the container
        container.appendChild(messageDiv);

        return messageDiv; // Return the created message element
    });
}

// Get container bounding rect
const containerRect = container.getBoundingClientRect();

let idx = 0;

// Compute target translate distance (30px from the top)
function getTargetY() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const containerTop = container.getBoundingClientRect().top + scrollTop;
    return TARGET_TOP - containerTop;
}

// Create per-message slide animation (allows multiple to move up simultaneously)
function slideMessage(msg) {
    // Initial state
    msg.style.opacity = '1';
    msg.style.pointerEvents = 'auto';
    msg.style.zIndex = 2;

    // Clear transform before animating to ensure correct positioning
    msg.style.transition = 'none';
    msg.style.transform = 'translateY(60px) scale(0.96)';

    // Force reflow to ensure transition takes effect
    void msg.offsetWidth;

    // Slide-in phase
    msg.style.transition = `transform ${SLIDE_IN_DURATION}ms cubic-bezier(.62,1.78,.56,1.1), opacity ${SLIDE_IN_DURATION}ms`;
    msg.style.transform = 'translateY(0) scale(1)';
    msg.style.opacity = '1';

    // After slide-in ends, switch to continuous upward move (do not hide immediately)
    setTimeout(() => {
        // Compute target Y (30px from the top)
        const targetY = getTargetY();

        // Move up continuously and fade out
        msg.style.transition = `transform ${MOVE_DURATION}ms linear, opacity 600ms ${MOVE_DURATION - 600}ms`;
        msg.style.transform = `translateY(${targetY}px) scale(0.98)`;
        msg.style.opacity = '0';

        // Once at the top and faded, fully hide and release z-index
        setTimeout(() => {
            msg.style.transition = 'none';
            msg.style.opacity = '0';
            msg.style.zIndex = 1;
        }, MOVE_DURATION);

    }, SLIDE_IN_DURATION);
}

var timeout_id = null;

function play_plaza_message() {
    // Start current message animation
    if (messages.length > 0) {
        slideMessage(messages[idx]);

        // Schedule the next message after WAIT_BEFORE_NEXT
        idx = (idx + 1) % messages.length;
        timeout_id = setTimeout(play_plaza_message, SLIDE_IN_DURATION + WAIT_BEFORE_NEXT);
    }
}

// Fetch network data after page load
document.addEventListener('DOMContentLoaded', () => {
    fetchMessageData();
});

// Recompute animation endpoint on window resize
window.addEventListener('resize', () => {
    // Reposition endpoints for messages currently sliding
    messages.forEach(msg => {
        const style = window.getComputedStyle(msg);
        if (style.opacity !== "0" && style.transform !== "none") {
            const matrix = new DOMMatrixReadOnly(style.transform);
            if (matrix.m42 !== 0 && matrix.m42 !== 60) { // already sliding upward
                const targetY = getTargetY();
                msg.style.transition = ''; // clear transition and reposition immediately
                msg.style.transform = `translateY(${targetY}px) scale(0.98)`;
            }
        }
    });
});

// Stop message rotation
function stop_plaza_message() {
    // Clear all pending timeouts
        if(timeout_id) {
            window.clearTimeout(timeout_id);
        }else{return true}

    // Reset styles for all messages
    messages.forEach(msg => {
        msg.style.transition = 'none';
        msg.style.opacity = '0';
        msg.style.transform = 'translateY(60px) scale(0.96)';
        msg.style.pointerEvents = 'none';
        msg.style.zIndex = 1;
    });
}
