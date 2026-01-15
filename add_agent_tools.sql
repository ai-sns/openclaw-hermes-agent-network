-- ============================================
-- Agent工具关联配置脚本
-- 执行前请先停止 api_server.py
-- ============================================

-- 1. 创建agent_tools表（如果不存在）
CREATE TABLE IF NOT EXISTS agent_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    tool_type TEXT NOT NULL,  -- 'plugin', 'mcp', 'function', 'skill'
    tool_id TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_cfg(id)
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_agent_tools_agent ON agent_tools(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_tools_type ON agent_tools(tool_type, tool_id);

-- 3. 清空Agent 1的现有工具配置（如果有的话）
DELETE FROM agent_tools WHERE agent_id = 1;

-- 4. 为Agent 1 添加工具关联
-- 注意：根据您数据库中实际存在的工具ID进行调整

-- 添加高德地图MCP (stdio版本) - 可以查询位置、路线等
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'mcp', 'ZP2025061314162230222', 1, 10);

-- 添加DuckDuckGo搜索MCP - 可以搜索信息
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'mcp', 'LD2025061314404887010', 1, 9);

-- 可选：添加其他MCP工具
-- INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
-- VALUES (1, 'mcp', 'BK2025061220454036750', 1, 8);  -- mcp001

-- 5. 验证配置
SELECT
    at.id,
    at.agent_id,
    at.tool_type,
    at.tool_id,
    CASE at.tool_type
        WHEN 'plugin' THEN (SELECT name FROM pluginmng WHERE plugin_id = at.tool_id)
        WHEN 'mcp' THEN (SELECT name FROM mcp_mng WHERE mcp_id = at.tool_id)
        WHEN 'function' THEN (SELECT name FROM function_mng WHERE function_id = at.tool_id)
        WHEN 'skill' THEN (SELECT name FROM skill_mng WHERE skill_id = at.tool_id)
    END as tool_name,
    at.enabled,
    at.priority,
    at.create_time
FROM agent_tools at
WHERE at.agent_id = 1
ORDER BY at.priority DESC;

-- 完成提示
SELECT '✓ Agent工具配置完成！' as message;
SELECT '请重启 api_server.py 使配置生效' as next_step;
