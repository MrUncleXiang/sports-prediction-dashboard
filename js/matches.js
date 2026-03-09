/**
 * 比赛数据查看页面逻辑
 * 功能：数据加载、筛选、排序、分页、导出
 */

// ===== 全局状态 =====
let allMatches = [];          // 所有比赛数据
let filteredMatches = [];     // 筛选后的数据
let currentPage = 1;          // 当前页码
let pageSize = 100;           // 每页显示数量
let sortColumn = 'match_date'; // 当前排序列
let sortOrder = 'desc';       // 排序方向 (asc/desc)

// 数据基础路径（支持 GitHub Pages 子路径）
const getBasePath = () => {
    const path = window.location.pathname;
    const base = path.endsWith('/') ? path.slice(0, -1) : path;
    return base || '';
};
const DATA_BASE = getBasePath() + '/data';

// 联赛名称映射
const LEAGUE_NAMES = {
    'epl': '英超',
    'pl': '英超',
    'laliga': '西甲',
    'bundesliga': '德甲',
    'seriea': '意甲',
    'ligue1': '法甲',
    'ligue_1': '法甲',
    'nba': 'NBA'
};

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    setupEventListeners();
});

// ===== 数据加载 =====
async function loadData() {
    const loadingEl = document.getElementById('loading');
    const mainContentEl = document.getElementById('main-content');
    
    try {
        console.log('[DEBUG] 开始加载数据，DATA_BASE:', DATA_BASE);
        
        const cacheBuster = `?t=${Date.now()}`;
        const response = await fetch(`${DATA_BASE}/matches.json${cacheBuster}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('[DEBUG] 数据加载成功，比赛数量:', data.matches?.length || 0);
        
        allMatches = data.matches || [];
        
        // 更新元数据显示
        if (data.metadata) {
            updateMetadata(data.metadata);
            populateFilters(data.metadata);
        }
        
        // 应用初始筛选（显示全部）
        filteredMatches = [...allMatches];
        
        // 初始排序
        sortMatches();
        
        // 渲染表格
        renderTable();
        
        // 显示主内容
        loadingEl.style.display = 'none';
        mainContentEl.style.display = 'block';
        
    } catch (error) {
        console.error('[ERROR] 数据加载失败:', error);
        loadingEl.innerHTML = `
            <div class="error-message">
                <h3 style="color: #dc2626; margin-bottom: 15px;">⚠️ 数据加载失败</h3>
                <p style="margin-bottom: 10px;"><strong>错误信息：</strong>${error.message}</p>
                <p style="margin-bottom: 10px;"><strong>数据路径：</strong>${DATA_BASE}/matches.json</p>
                <p style="margin-bottom: 20px; opacity: 0.8;">请检查：</p>
                <ul style="margin-bottom: 20px; padding-left: 20px; opacity: 0.8;">
                    <li>数据文件是否存在</li>
                    <li>JSON 格式是否正确</li>
                    <li>是否已运行数据生成脚本</li>
                </ul>
                <button onclick="location.reload()" class="btn btn-primary">🔄 刷新页面</button>
            </div>
        `;
    }
}

// ===== 元数据更新 =====
function updateMetadata(metadata) {
    const updateTimeEl = document.getElementById('data-update-time');
    if (updateTimeEl && metadata.generated_at) {
        const date = new Date(metadata.generated_at);
        updateTimeEl.textContent = date.toLocaleString('zh-CN');
    }
}

// ===== 填充筛选选项 =====
function populateFilters(metadata) {
    // 赛季筛选
    const seasonFilter = document.getElementById('season-filter');
    if (metadata.seasons && metadata.seasons.length > 0) {
        seasonFilter.innerHTML = metadata.seasons
            .sort((a, b) => b.localeCompare(a)) // 倒序排列
            .map(season => `<option value="${season}">${season}</option>`)
            .join('');
    }
    
    // 轮次筛选
    const roundFilter = document.getElementById('round-filter');
    if (metadata.rounds && metadata.rounds.length > 0) {
        roundFilter.innerHTML = metadata.rounds
            .sort((a, b) => a - b)
            .map(round => `<option value="${round}">第${round}轮</option>`)
            .join('');
    }
}

// ===== 事件监听器 =====
function setupEventListeners() {
    // 表格列排序
    document.querySelectorAll('.data-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            handleSort(column);
        });
    });
    
    // 球队搜索防抖
    let debounceTimer;
    const teamFilter = document.getElementById('team-filter');
    teamFilter.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            applyFilters();
        }, 500);
    });
}

// ===== 筛选功能 =====
function getFilterValues() {
    const leagueFilter = document.getElementById('league-filter');
    const seasonFilter = document.getElementById('season-filter');
    const roundFilter = document.getElementById('round-filter');
    const teamFilter = document.getElementById('team-filter');
    const statusFilter = document.querySelector('input[name="status-filter"]:checked');
    
    return {
        leagues: Array.from(leagueFilter.selectedOptions).map(opt => opt.value),
        seasons: Array.from(seasonFilter.selectedOptions).map(opt => opt.value),
        rounds: Array.from(roundFilter.selectedOptions).map(opt => opt.value),
        team: teamFilter.value.trim().toLowerCase(),
        status: statusFilter.value
    };
}

function applyFilters() {
    const filters = getFilterValues();
    
    filteredMatches = allMatches.filter(match => {
        // 联赛筛选
        if (filters.leagues.length > 0 && !filters.leagues.includes(match.league_code)) {
            return false;
        }
        
        // 赛季筛选
        if (filters.seasons.length > 0 && !filters.seasons.includes(match.season)) {
            return false;
        }
        
        // 轮次筛选
        if (filters.rounds.length > 0 && !filters.rounds.includes(String(match.round))) {
            return false;
        }
        
        // 球队筛选
        if (filters.team && 
            !match.home_team.toLowerCase().includes(filters.team) && 
            !match.away_team.toLowerCase().includes(filters.team)) {
            return false;
        }
        
        // 状态筛选
        if (filters.status === 'FINISHED' && match.status !== 'FINISHED') {
            return false;
        }
        if (filters.status === 'SCHEDULED' && match.status === 'FINISHED') {
            return false;
        }
        
        return true;
    });
    
    // 重新排序
    sortMatches();
    
    // 重置到第一页
    currentPage = 1;
    
    // 渲染表格
    renderTable();
    
    // 更新筛选结果统计
    updateFilterStats();
}

function resetFilters() {
    // 重置所有筛选
    document.getElementById('league-filter').selectedIndex = -1;
    document.getElementById('season-filter').selectedIndex = -1;
    document.getElementById('round-filter').selectedIndex = -1;
    document.getElementById('team-filter').value = '';
    document.querySelector('input[name="status-filter"][value="all"]').checked = true;
    
    // 重新应用筛选
    applyFilters();
}

function updateFilterStats() {
    const countEl = document.getElementById('filter-result-count');
    if (countEl) {
        countEl.textContent = `共 ${filteredMatches.length} 场比赛`;
    }
}

// ===== 排序功能 =====
function handleSort(column) {
    if (sortColumn === column) {
        // 切换排序方向
        sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        // 新列，默认降序
        sortColumn = column;
        sortOrder = 'desc';
    }
    
    // 更新排序指示器
    document.querySelectorAll('.sort-indicator').forEach(indicator => {
        indicator.textContent = '↕';
    });
    
    const currentTh = document.querySelector(`th[data-sort="${column}"] .sort-indicator`);
    if (currentTh) {
        currentTh.textContent = sortOrder === 'asc' ? '↑' : '↓';
    }
    
    sortMatches();
    renderTable();
}

function sortMatches() {
    filteredMatches.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];
        
        // 特殊处理比分列
        if (sortColumn === 'score') {
            aVal = a.home_score ?? -1;
            bVal = b.home_score ?? -1;
        }
        
        // 处理空值
        if (aVal === null || aVal === undefined) aVal = '';
        if (bVal === null || bVal === undefined) bVal = '';
        
        // 比较
        if (typeof aVal === 'string' && typeof bVal === 'string') {
            const cmp = aVal.localeCompare(bVal, 'zh-CN');
            return sortOrder === 'asc' ? cmp : -cmp;
        } else {
            const cmp = aVal < bVal ? -1 : (aVal > bVal ? 1 : 0);
            return sortOrder === 'asc' ? cmp : -cmp;
        }
    });
}

// ===== 表格渲染 =====
function renderTable() {
    const tbody = document.getElementById('table-body');
    const totalPages = Math.ceil(filteredMatches.length / pageSize);
    
    // 边界检查
    if (currentPage > totalPages) currentPage = totalPages || 1;
    if (currentPage < 1) currentPage = 1;
    
    // 计算分页
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageData = filteredMatches.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">暂无匹配的比赛数据</div>
                    <div style="font-size: 0.9em; margin-top: 10px;">尝试调整筛选条件</div>
                </td>
            </tr>
        `;
    } else {
        tbody.innerHTML = pageData.map(match => {
            const isFinished = match.status === 'FINISHED';
            const score = isFinished 
                ? `<span class="score">${match.home_score ?? '-'}-${match.away_score ?? '-'}</span>`
                : `<span class="score pending">-:-</span>`;
            const statusBadge = isFinished
                ? '<span class="badge badge-success">已结束</span>'
                : '<span class="badge badge-info">未开始</span>';
            
            const date = match.match_date ? new Date(match.match_date) : null;
            const dateStr = date 
                ? date.toLocaleString('zh-CN', { 
                    month: '2-digit', 
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                })
                : '-';
            
            return `
                <tr>
                    <td>${match.round || '-'}</td>
                    <td>${dateStr}</td>
                    <td>${match.league_name || match.league_code}</td>
                    <td><strong>${match.home_team}</strong></td>
                    <td class="text-center">${score}</td>
                    <td><strong>${match.away_team}</strong></td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    }
    
    // 更新分页信息
    updatePagination(totalPages);
}

// ===== 分页功能 =====
function updatePagination(totalPages) {
    const pageInfoEl = document.getElementById('page-info');
    const btnFirst = document.getElementById('btn-first');
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    const btnLast = document.getElementById('btn-last');
    
    if (pageInfoEl) {
        pageInfoEl.textContent = `${currentPage} / ${totalPages || 1}`;
    }
    
    // 按钮状态
    if (btnFirst) btnFirst.disabled = currentPage === 1;
    if (btnPrev) btnPrev.disabled = currentPage === 1;
    if (btnNext) btnNext.disabled = currentPage === totalPages || totalPages === 0;
    if (btnLast) btnLast.disabled = currentPage === totalPages || totalPages === 0;
}

function firstPage() {
    currentPage = 1;
    renderTable();
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredMatches.length / pageSize);
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
}

function lastPage() {
    currentPage = Math.ceil(filteredMatches.length / pageSize) || 1;
    renderTable();
}

function changePageSize() {
    const select = document.getElementById('page-size');
    pageSize = parseInt(select.value);
    currentPage = 1;
    renderTable();
}

function jumpToPage() {
    const input = document.getElementById('page-jump-input');
    const page = parseInt(input.value);
    const totalPages = Math.ceil(filteredMatches.length / pageSize);
    
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        renderTable();
        input.value = '';
    } else {
        alert(`请输入有效页码 (1-${totalPages})`);
    }
}

// ===== 导出功能 =====
function exportCSV() {
    if (filteredMatches.length === 0) {
        alert('没有可导出的数据');
        return;
    }
    
    // CSV 表头
    const headers = ['轮次', '日期', '联赛', '主队', '比分', '客队', '状态'];
    
    // CSV 数据行
    const rows = filteredMatches.map(match => {
        const date = match.match_date ? new Date(match.match_date) : null;
        const dateStr = date 
            ? date.toLocaleString('zh-CN', { 
                year: 'numeric',
                month: '2-digit', 
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            })
            : '-';
        
        const score = match.status === 'FINISHED'
            ? `${match.home_score ?? '-'}-${match.away_score ?? '-'}`
            : '-:-';
        
        const status = match.status === 'FINISHED' ? '已结束' : '未开始';
        
        return [
            match.round || '-',
            dateStr,
            match.league_name || match.league_code,
            match.home_team,
            score,
            match.away_team,
            status
        ];
    });
    
    // 生成 CSV 内容（添加 BOM 以支持 Excel 中文）
    const csvContent = '\uFEFF' + [headers, ...rows]
        .map(row => row.map(cell => {
            // 处理包含逗号或引号的单元格
            const str = String(cell);
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        }).join(','))
        .join('\n');
    
    downloadFile(csvContent, `matches_${new Date().toISOString().slice(0, 10)}.csv`, 'text/csv;charset=utf-8;');
}

function exportJSON() {
    if (filteredMatches.length === 0) {
        alert('没有可导出的数据');
        return;
    }
    
    const jsonData = JSON.stringify(filteredMatches, null, 2);
    downloadFile(jsonData, `matches_${new Date().toISOString().slice(0, 10)}.json`, 'application/json');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ===== 工具函数 =====
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', { 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ===== 调试工具（开发用）=====
window.debugMatches = {
    getAll: () => allMatches,
    getFiltered: () => filteredMatches,
    getStats: () => ({
        total: allMatches.length,
        filtered: filteredMatches.length,
        currentPage,
        pageSize,
        totalPages: Math.ceil(filteredMatches.length / pageSize)
    })
};

console.log('[INFO] 比赛数据查看页面已加载，输入 debugMatches 查看调试信息');
