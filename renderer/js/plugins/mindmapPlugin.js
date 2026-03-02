/**
 * Mindmap Plugin - mind map plugin
 * Convert Markdown mindmap syntax into a visual mind map
 */

const MindmapPlugin = {
    /**
     * Plugin info
     */
    info: {
        id: 'mindmap',
        name: 'Mind Map Plugin',
        version: '1.0.0',
        description: 'Convert Markdown mindmap syntax into a visual mind map'
    },

    /**
     * Parse mindmap markdown syntax
     * Supported format:
     * ```mindmap
     * - Root
     *   - Child 1
     *     - Subchild 1.1
     *   - Child 2
     * ```
     */
    parseMindmap(markdown) {
        const lines = markdown.trim().split('\n');
        const root = { text: '', children: [], level: -1 };
        const stack = [root];

        lines.forEach(line => {
            // Compute indentation level
            const match = line.match(/^(\s*)-\s+(.+)$/);
            if (!match) return;

            const indent = match[1].length;
            const level = Math.floor(indent / 2);
            const text = match[2].trim();

            const node = {
                text,
                children: [],
                level
            };

            // Find parent node
            while (stack.length > 0 && stack[stack.length - 1].level >= level) {
                stack.pop();
            }

            const parent = stack[stack.length - 1];
            parent.children.push(node);
            stack.push(node);
        });

        return root.children[0] || root;
    },

    /**
     * Render mind map to SVG
     */
    renderToSVG(data, width = 800, height = 600) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        // Get current theme background color from CSS variables
        const bgColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--bg-secondary').trim() || '#f8f9fa';

        svg.style.background = bgColor;
        svg.style.borderRadius = '8px';

        // Define styles
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');

        // Use CSS variables
        const primaryColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--color-primary').trim() || '#1976d2';
        const textColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-primary').trim() || '#333';
        const borderColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--border-color').trim() || '#90caf9';

        style.textContent = `
            .mindmap-node { cursor: pointer; transition: all 0.2s ease; }
            .mindmap-node:hover rect { fill: ${primaryColor}22; stroke: ${primaryColor}; }
            .mindmap-node text { pointer-events: none; user-select: none; }
            .mindmap-link { fill: none; stroke: ${borderColor}; stroke-width: 2; }
        `;
        defs.appendChild(style);
        svg.appendChild(defs);

        // Calculate node positions
        const nodeWidth = 120;
        const nodeHeight = 40;
        const levelSpacing = 180;
        const nodeSpacing = 60;

        const positions = new Map();
        const calculatePositions = (node, level = 0, yOffset = 0) => {
            const x = level * levelSpacing + 50;
            const y = yOffset * nodeSpacing + 50;
            positions.set(node, { x, y });

            let childOffset = yOffset;
            node.children.forEach(child => {
                calculatePositions(child, level + 1, childOffset);
                childOffset++;
            });

            return childOffset;
        };

        calculatePositions(data);

        // Render links
        const renderLinks = (node) => {
            const pos = positions.get(node);
            node.children.forEach(child => {
                const childPos = positions.get(child);
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

                const startX = pos.x + nodeWidth;
                const startY = pos.y + nodeHeight / 2;
                const endX = childPos.x;
                const endY = childPos.y + nodeHeight / 2;
                const midX = (startX + endX) / 2;

                const d = `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
                path.setAttribute('d', d);
                path.setAttribute('class', 'mindmap-link');
                svg.appendChild(path);

                renderLinks(child);
            });
        };

        renderLinks(data);

        // Render nodes
        const renderNodes = (node, index = 0) => {
            const pos = positions.get(node);
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', 'mindmap-node');
            g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);

            // Node background
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('width', nodeWidth);
            rect.setAttribute('height', nodeHeight);
            rect.setAttribute('rx', '8');
            rect.setAttribute('fill', index === 0 ? primaryColor : bgColor);
            rect.setAttribute('stroke', index === 0 ? primaryColor : borderColor);
            rect.setAttribute('stroke-width', '2');
            g.appendChild(rect);

            // Node text
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', nodeWidth / 2);
            text.setAttribute('y', nodeHeight / 2 + 5);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', index === 0 ? '#fff' : textColor);
            text.setAttribute('font-size', '13');
            text.setAttribute('font-weight', index === 0 ? 'bold' : 'normal');
            text.textContent = node.text.length > 15 ? node.text.substring(0, 15) + '...' : node.text;

            // Add title to show full text
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = node.text;
            text.appendChild(title);

            g.appendChild(text);
            svg.appendChild(g);

            node.children.forEach((child, i) => renderNodes(child, i + 1));
        };

        renderNodes(data);

        return svg;
    },

    /**
     * Detect whether the message contains mindmap
     */
    detectMindmap(content) {
        // Detect raw markdown format
        const mindmapRegex = /```mindmap\s*([\s\S]*?)\s*```/gi;
        const matches = [];
        let match;

        while ((match = mindmapRegex.exec(content)) !== null) {
            matches.push({
                fullMatch: match[0],
                content: match[1],
                index: match.index
            });
        }

        console.log('[MindmapPlugin] Detected mindmaps:', matches.length);
        return matches;
    },

    /**
     * Render mind map into message
     */
    renderInMessage(messageBody) {
        console.log('[MindmapPlugin] ========== Start checking messages ==========');

        // Find all code block elements directly
        const codeBlocks = messageBody.querySelectorAll('.code-block');
        console.log('[MindmapPlugin] Code blocks found:', codeBlocks.length);

        let renderedCount = 0;

        codeBlocks.forEach((block, blockIndex) => {
            const langSpan = block.querySelector('.code-lang');
            const codeElement = block.querySelector('code');

            console.log(`[MindmapPlugin] Code block ${blockIndex + 1}:`, {
                hasLangSpan: !!langSpan,
                language: langSpan ? langSpan.textContent : 'null',
                hasCodeElement: !!codeElement,
                codeLength: codeElement ? codeElement.textContent.length : 0
            });

            if (langSpan && langSpan.textContent.toLowerCase().trim() === 'mindmap' && codeElement) {
                try {
                    console.log('[MindmapPlugin] ✓ Mindmap code block detected');

                    // Get raw code content
                    const mindmapContent = codeElement.dataset.rawCode || codeElement.textContent;
                    console.log('[MindmapPlugin] Code content:', mindmapContent.substring(0, 100) + '...');

                    // Parse mind map data
                    const data = this.parseMindmap(mindmapContent);
                    console.log('[MindmapPlugin] Parsed result:', data);

                    if (!data || (!data.text && data.children.length === 0)) {
                        console.error('[MindmapPlugin] ✗ Parse failed or data is empty');
                        return;
                    }

                    // Render to SVG
                    const svg = this.renderToSVG(data);
                    console.log('[MindmapPlugin] ✓ SVG created');

                    // Create container
                    const container = document.createElement('div');
                    container.className = 'mindmap-container';
                    container.style.cssText = `
                        margin: 16px 0;
                        padding: 16px;
                        background: var(--bg-secondary, #f8f9fa);
                        border-radius: 8px;
                        border: 1px solid var(--border-light, #e0e0e0);
                        overflow-x: auto;
                    `;

                    // Add title
                    const title = document.createElement('div');
                    title.style.cssText = `
                        font-size: 13px;
                        color: var(--text-secondary, #666);
                        margin-bottom: 12px;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    `;
                    title.innerHTML = `
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="var(--color-primary, #1976d2)">
                            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                        </svg>
                        <span>Mind map</span>
                    `;
                    container.appendChild(title);

                    // Add SVG
                    container.appendChild(svg);

                    // Replace code block
                    block.replaceWith(container);
                    renderedCount++;
                    console.log('[MindmapPlugin] ✓ Replaced with mind map visualization');
                } catch (error) {
                    console.error('[MindmapPlugin] ✗ Render failed:', error);
                    console.error(error.stack);
                }
            }
        });

        console.log('[MindmapPlugin] ========== Check complete, rendered', renderedCount, 'mind maps ==========');
        return renderedCount > 0;
    },

    /**
     * Generate example mindmap markdown
     */
    getExample() {
        return `\`\`\`mindmap
 - Learn programming
  - Fundamentals
    - Data types
    - Control flow
    - Functions
  - Hands-on projects
    - Web development
    - Mobile apps
    - Data analysis
  - Advanced learning
    - Algorithms and data structures
    - Design patterns
    - System architecture
\`\`\``;
    }
};

// Export plugin
if (typeof window !== 'undefined') {
    window.MindmapPlugin = MindmapPlugin;
}

export default MindmapPlugin;
