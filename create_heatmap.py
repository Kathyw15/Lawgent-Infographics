#!/usr/bin/env python3
"""
Generate an interactive heatmap visualization for H1B sponsor data
"""

import csv
import re
from pathlib import Path

def parse_number(value):
    """Parse number with commas, quotes, and spaces"""
    if not value or value == '':
        return 0
    # Remove quotes, spaces, and commas
    cleaned = str(value).strip().replace('"', '').replace("'", '').replace(',', '').replace(' ', '')
    try:
        return int(cleaned)
    except (ValueError, AttributeError):
        return 0

def parse_ranking_change(value):
    """Parse ranking change (e.g., ⬇️1, ⬆️1)"""
    if not value or value == '':
        return None, None
    if '⬇️' in value:
        direction = 'down'
        num = re.search(r'\d+', value)
        change = int(num.group()) if num else 0
    elif '⬆️' in value:
        direction = 'up'
        num = re.search(r'\d+', value)
        change = int(num.group()) if num else 0
    else:
        return None, None
    return direction, change

def read_csv_data(csv_path, year=None):
    """Read and parse CSV data, supporting multiple column name formats"""
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows or summary rows
            rank = row.get('rank', '').strip()
            if not rank or not rank.isdigit():
                continue
            
            # Support different column name formats
            name = (row.get('简称 Employer (Petitioner) Name', '') or 
                   row.get('Employer (Petitioner) Name', '')).strip()
            if not name:
                continue
            
            full_name = row.get('全名 Employer (Petitioner) Name', '').strip()
            # 如果没有全名，使用简称
            if not full_name:
                full_name = name
            
            is_icc = row.get('是否ICC', '').strip() == 'Y'
            # Support different column names for beneficiaries
            beneficiaries_str = row.get('Beneficiaries Approved', '') or row.get('TOTAL', '')
            beneficiaries = parse_number(beneficiaries_str) if beneficiaries_str else 0
            rank_change = row.get('排名变化', '').strip()
            
            direction, change = parse_ranking_change(rank_change)
            
            companies.append({
                'rank': int(rank),
                'is_icc': is_icc,
                'name': name,
                'full_name': full_name,
                'beneficiaries': beneficiaries,
                'rank_change_direction': direction,
                'rank_change_value': change,
                'year': year
            })
    
    return companies

def generate_heatmap_html(all_years_data):
    """Generate HTML treemap heatmap where size is proportional to beneficiaries
    all_years_data: dict with year as key and list of companies as value
    Example: {2016: [...], 2017: [...], ..., 2025: [...]}
    """
    
    # Brand colors mapping
    brand_colors = {
        'Amazon': '#FF9900',
        'Meta': '#0081FB',
        'Microsoft': '#00A4EF',
        'TCS': '#0070AD',
        'Google': '#4285F4',
        'Apple': '#000000',
        'Cognizant': '#0066CC',
        'Walmart': '#0071CE',
        'Deloitte': '#86BC25',
        'JPMorgan Chase': '#0066CC',
        'Infosys': '#0073BC',
        'Oracle': '#F80000',
        'EY': '#FFCC00',
        'HCL': '#FF6600',
        'Capgemini': '#0070AD',
        'Intel': '#0071C5',
        'Cisco': '#1BA0D7',
        'IBM': '#006699',
        'Accenture': '#A100FF',
        'NVIDIA': '#76B900',
        'Wipro': '#FF6600',
        'Fidelity': '#0171BB',
        'Fidelity Investments': '#0171BB',
        'Salesforce': '#00A1E0',
        'LTIMindtree': '#0066CC',
        'Citibank': '#0066CC',
        'Qualcomm': '#3253DC',
        'Tech Mahindra': '#C72E2E',
        'Tesla': '#E31937',
        'Goldman Sachs': '#000000',
        'PayPal': '#003087',
        'Compunnel': '#8B4513',
        'LinkedIn': '#0077B5'
    }
    
    # Also create a mapping for case-insensitive lookup
    brand_colors_lower = {k.lower(): v for k, v in brand_colors.items()}
    
    # 计算当年相对于上一年的排名变化
    def calculate_rank_changes(prev_companies, current_companies):
        """计算当年相对于上一年的排名变化
        原则：
        - 如果对比上一年无变化，不显示变化标签（rank_change_direction=None）
        - 如果对比上一年排名下降，显示下降多少名
        - 如果对比上一年排名上升，显示上升多少名
        """
        if not prev_companies or not current_companies:
            return current_companies
        
        # 创建上一年公司名称到排名的映射
        prev_rank_map = {}
        for c in prev_companies:
            name_key = c['name'].lower().strip()
            prev_rank_map[name_key] = c['rank']
        
        # 为当年的公司重新计算排名变化（忽略CSV中的数据，确保准确性）
        for c in current_companies:
            name_key = c['name'].lower().strip()
            if name_key in prev_rank_map:
                prev_rank = prev_rank_map[name_key]
                current_rank = c['rank']
                change = prev_rank - current_rank  # 正数表示上升，负数表示下降
                
                if change > 0:
                    # 排名上升
                    c['rank_change_direction'] = 'up'
                    c['rank_change_value'] = change
                elif change < 0:
                    # 排名下降
                    c['rank_change_direction'] = 'down'
                    c['rank_change_value'] = abs(change)
                else:
                    # 排名无变化，不显示标签
                    c['rank_change_direction'] = None
                    c['rank_change_value'] = None
            else:
                # 新进入的公司，不显示排名变化
                c['rank_change_direction'] = None
                c['rank_change_value'] = None
        
        return current_companies
    
    # 生成颜色：非ICC公司绿色系，ICC公司紫色系，低饱和度，不同深浅
    def generate_color(is_icc, index, total):
        """根据是否为ICC公司生成颜色，使用低饱和度，不同色块有不同深浅"""
        if is_icc:
            # 紫色系：低饱和度，从浅紫到深紫
            hue = 270  # 紫色色调
            saturation = 15 + (index / total) * 15  # 15-30% 低饱和度
            # 根据排名位置生成不同深浅，确保有明显区别
            lightness = 85 - (index / total) * 25  # 85-60% 从浅到深
        else:
            # 绿色系：低饱和度，从浅绿到深绿
            hue = 140  # 绿色色调
            saturation = 15 + (index / total) * 15  # 15-30% 低饱和度
            # 根据排名位置生成不同深浅，确保有明显区别
            lightness = 85 - (index / total) * 25  # 85-60% 从浅到深
        
        return f"hsl({hue}, {saturation}%, {lightness}%)"
    
    # 处理数据并添加颜色
    def process_companies(companies_list):
        companies_sorted = sorted(companies_list, key=lambda x: x['beneficiaries'], reverse=True)
        result = []
        
        # 根据所有公司的排名位置生成颜色，ICC公司用紫色系，非ICC公司用绿色系
        # 每个色块根据它在所有公司中的位置有不同的深浅
        for idx, c in enumerate(companies_sorted):
            result.append({
                'name': c['name'],
                'full_name': c['full_name'],
                'beneficiaries': c['beneficiaries'],
                'rank': c['rank'],
                'is_icc': c['is_icc'],
                'rank_change_direction': c['rank_change_direction'],
                'rank_change_value': c['rank_change_value'],
                'brand_color': generate_color(c['is_icc'], idx, len(companies_sorted))
            })
        
        return result
    
    # 处理所有年份的数据
    import json
    years = sorted(all_years_data.keys())
    
    # 为每个年份计算排名变化（相对于前一年）
    processed_years = {}
    for i, year in enumerate(years):
        companies = all_years_data[year]
        # 如果有前一年的数据，计算排名变化
        if i > 0:
            prev_year = years[i-1]
            prev_companies = all_years_data[prev_year]
            companies = calculate_rank_changes(prev_companies, companies)
        
        processed_years[year] = process_companies(companies)
    
    # 生成所有年份的JSON数据
    years_json = {}
    for year in years:
        years_json[year] = json.dumps(processed_years[year], ensure_ascii=False)
    
    # 计算每个年份的统计数据
    stats_by_year = {}
    for year in years:
        companies = all_years_data[year]
        stats_by_year[year] = {
            'count': len(companies),
            'total': sum(c['beneficiaries'] for c in companies),
            'icc_count': len([c for c in companies if c['is_icc']])
        }
    
    # 为JavaScript准备统计数据
    stats_js = {}
    for year in years:
        stats = stats_by_year[year]
        stats_js[year] = f"{{count: {stats['count']}, total: {stats['total']}, icc_count: {stats['icc_count']}}}"
    
    # 默认显示最新年份
    default_year = max(years) if years else None
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>H1B Sponsor Company Heatmap</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: white;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 30px;
        }}
        
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        
        #treemap {{
            width: 100%;
            height: 800px;
            margin-top: 30px;
            position: relative;
        }}
        
        .treemap-cell {{
            position: absolute;
            border: 2px solid rgba(0, 0, 0, 0.1);
            cursor: pointer;
            transition: all 0.2s ease;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 4px;
        }}
        
        .treemap-cell:hover {{
            border-color: rgba(0, 0, 0, 0.3);
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        
        .cell-content {{
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
        }}
        
        .cell-logo-container {{
            position: absolute;
            top: 20px;
            left: 4px;
            z-index: 5;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            max-width: calc(100% - 8px);
        }}
        
        .cell-company-name {{
            margin-top: 4px;
            font-size: 0.65em;
            font-weight: bold;
            color: #333;
            line-height: 1.2;
            word-break: break-word;
            max-width: 100%;
            text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
            background: rgba(255, 255, 255, 0.7);
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        .cell-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2px;
        }}
        
        .cell-rank {{
            font-size: 0.7em;
            font-weight: bold;
            opacity: 0.9;
        }}
        
        .cell-icc-badge {{
            background: #ff6b6b;
            color: white;
            padding: 1px 4px;
            border-radius: 2px;
            font-size: 0.6em;
            font-weight: bold;
        }}
        
        .cell-name {{
            font-weight: bold;
            font-size: 0.9em;
            line-height: 1.2;
            margin-bottom: 4px;
            word-break: break-word;
        }}
        
        .cell-value {{
            font-size: 0.9em;
            font-weight: bold;
            margin-top: auto;
        }}
        
        .cell-change {{
            font-size: 0.9em;
            font-weight: bold;
            position: absolute;
            bottom: 2px;
            right: 2px;
            padding: 2px 6px;
            border-radius: 3px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            line-height: 1.2;
            z-index: 10;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 2px;
            background: rgba(255, 255, 255, 0.95);
        }}
        
        .cell-logo {{
            width: auto;
            height: auto;
            object-fit: contain;
            opacity: 0.7;
        }}
        
        .cell-change.up {{
            color: #27ae60;
        }}
        
        .cell-change.down {{
            color: #e74c3c;
        }}
        
        .cell-change-arrow {{
            font-size: 1.2em;
            font-weight: bold;
            line-height: 1;
        }}
        
        .legend {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .legend-color {{
            width: 30px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .tooltip {{
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
            font-size: 0.9em;
            max-width: 300px;
        }}
        
        .tooltip.show {{
            opacity: 1;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            flex-wrap: wrap;
            gap: 20px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #9EBA83;
        }}
        
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        
        .year-selector {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 40px auto;
            padding: 20px;
            position: relative;
            max-width: 90%;
        }}
        
        .timeline {{
            display: flex;
            align-items: center;
            width: 100%;
            position: relative;
            justify-content: space-between;
        }}
        
        .timeline-line {{
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 3px;
            background: #9EBA83;
            transform: translateY(-50%);
            z-index: 1;
        }}
        
        .year-button {{
            position: relative;
            z-index: 2;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 3px solid #9EBA83;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            padding: 0;
            margin: 0;
        }}
        
        .year-number {{
            display: none;
        }}
        
        .year-button:hover {{
            transform: scale(1.15);
            box-shadow: 0 4px 12px rgba(158, 186, 131, 0.4);
        }}
        
        .year-button.active {{
            background: #9EBA83;
            border-color: #9EBA83;
            transform: scale(1.3);
            box-shadow: 0 6px 16px rgba(158, 186, 131, 0.5);
            width: 20px;
            height: 20px;
        }}
        
        .year-button:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
            border-color: #ccc;
        }}
        
        .year-label {{
            position: absolute;
            top: calc(100% + 10px);
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.85em;
            white-space: nowrap;
            color: #666;
            font-weight: normal;
            pointer-events: none;
        }}
        
        .year-button.active .year-label {{
            font-weight: bold;
            color: #9EBA83;
            font-size: 0.95em;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            overflow: auto;
        }}
        
        .modal.show {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .modal-content {{
            background-color: white;
            margin: auto;
            padding: 30px;
            border-radius: 12px;
            max-width: 900px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .modal-title {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        
        .close-button {{
            background: none;
            border: none;
            font-size: 2em;
            cursor: pointer;
            color: #999;
            padding: 0;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.3s ease;
        }}
        
        .close-button:hover {{
            background: #f0f0f0;
            color: #333;
        }}
        
        #company-chart {{
            width: 100%;
            height: 500px;
            margin-top: 20px;
        }}
        
        .chart-bar {{
            fill: #9EBA83;
            transition: all 0.3s ease;
        }}
        
        .chart-bar:hover {{
            fill: #8BA872;
            opacity: 0.8;
        }}
        
        .chart-axis {{
            font-size: 12px;
            color: #666;
        }}
        
        .chart-label {{
            font-size: 11px;
            fill: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>H1B Sponsor Company Heatmap</h1>
        <p class="subtitle">Top 30 Companies by H1B Beneficiaries Approved (Size = Number of Beneficiaries)</p>
        
        <div class="year-selector">
            <div class="timeline">
                <div class="timeline-line"></div>
                {' '.join([f'<button class="year-button" id="year-{year}" onclick="switchYear({year})"><span class="year-number">{year}</span><span class="year-label">{year}</span></button>' for year in reversed(years)])}
            </div>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-item">
                <div class="stat-value" id="stat-count">{stats_by_year[default_year]['count'] if default_year else 0}</div>
                <div class="stat-label">Companies</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="stat-total">{stats_by_year[default_year]['total'] if default_year else 0:,}</div>
                <div class="stat-label">Total Beneficiaries</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="stat-icc">{stats_by_year[default_year]['icc_count'] if default_year else 0}</div>
                <div class="stat-label">ICC Companies</div>
            </div>
        </div>
        
        <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f0f4ff; border-radius: 8px; color: #9EBA83; font-size: 0.95em;">
            💡 点击公司名查看该公司历年H1B申请通过数趋势
        </div>
        
        <div id="treemap"></div>
        
        <div class="legend">
            <div class="legend-item">
                <div style="border: 2px solid #ff6b6b; padding: 2px 6px; border-radius: 4px;">ICC</div>
                <span>ICC Company</span>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <!-- 公司详情模态框 -->
    <div id="company-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modal-company-name">Company Name</h2>
                <button class="close-button" onclick="closeModal()">&times;</button>
            </div>
            <div>
                <h3 id="modal-chart-title" style="margin-bottom: 20px; color: #666;"></h3>
                <div id="company-chart"></div>
            </div>
        </div>
    </div>
    
    <script>
        // 所有年份的数据
        const allYearsData = {{
            {', '.join([f'{year}: {years_json[year]}' for year in years])}
        }};
        
        // 所有年份的统计数据
        const allYearsStats = {{
            {', '.join([f'{year}: {stats_js[year]}' for year in years])}
        }};
        
        const availableYears = [{', '.join(map(str, years))}];
        let currentYear = {default_year if default_year else 'null'};
        let currentCompanies = allYearsData[currentYear] || [];
        
        // 初始化：默认显示最新年份
        if (currentYear !== null) {{
            document.getElementById(`year-${{currentYear}}`).classList.add('active');
        }}
        
        // 切换年份函数
        function switchYear(year) {{
            if (!allYearsData[year]) return;
            
            currentYear = year;
            currentCompanies = allYearsData[year];
            
            // 更新按钮状态
            document.querySelectorAll('.year-button').forEach(btn => {{
                btn.classList.remove('active');
            }});
            document.getElementById(`year-${{year}}`).classList.add('active');
            
            // 更新统计数据
            const stats = allYearsStats[year];
            if (stats) {{
                updateStats(stats.count, stats.total, stats.icc_count);
            }}
            
            updateTreemap();
        }}
        
        // 更新统计数据
        function updateStats(count, total, iccCount) {{
            document.getElementById('stat-count').textContent = count;
            document.getElementById('stat-total').textContent = total.toLocaleString();
            document.getElementById('stat-icc').textContent = iccCount;
        }}
        
        // 更新热力图
        function updateTreemap() {{
            // 清除现有内容
            d3.select('#treemap').selectAll('*').remove();
            
            // 重新创建热力图
            createTreemap();
        }}
        
        // 创建热力图函数
        function createTreemap() {{
            const companies = currentCompanies;
        
        // Convert hex color to RGB
        function hexToRgb(hex) {{
            const result = /^#?([a-f\\d]{{2}})([a-f\\d]{{2}})([a-f\\d]{{2}})$/i.exec(hex);
            return result ? {{
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16)
            }} : null;
        }}
        
        // Text color based on background (works with hex colors)
        function getTextColor(bgColor) {{
            const rgb = hexToRgb(bgColor);
            if (rgb) {{
                const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
                return brightness > 128 ? '#000' : '#fff';
            }}
            return '#000';
        }}
        
            // Create treemap
            const treemapContainer = d3.select('#treemap');
            const width = treemapContainer.node().offsetWidth;
            const height = 800;
            
            // Prepare data for D3 treemap
            const root = d3.hierarchy({{children: companies}})
                .sum(d => d.beneficiaries)
                .sort((a, b) => b.value - a.value);
            
            // Create treemap layout
            const treemap = d3.treemap()
                .size([width, height])
                .padding(2)
                .round(true);
            
            treemap(root);
            
            // Create cells
            const cells = treemapContainer.selectAll('.treemap-cell')
                .data(root.leaves())
                .enter()
                .append('div')
                .attr('class', d => `treemap-cell ${{d.data.is_icc ? 'icc' : ''}}`)
                .style('left', d => d.x0 + 'px')
                .style('top', d => d.y0 + 'px')
                .style('width', d => (d.x1 - d.x0) + 'px')
                .style('height', d => (d.y1 - d.y0) + 'px')
                .style('background-color', d => d.data.brand_color)
                .style('color', '#000')
                .on('mouseenter', function(event, d) {{
                    const tooltip = d3.select('#tooltip');
                    tooltip.html(`
                        <strong>${{d.data.name}}</strong><br>
                        ${{d.data.full_name}}<br>
                        Rank: #${{d.data.rank}}<br>
                        Beneficiaries: ${{d.data.beneficiaries.toLocaleString()}}
                    `);
                    tooltip.classed('show', true);
                }})
                .on('mouseleave', function() {{
                    d3.select('#tooltip').classed('show', false);
                }})
                .on('mousemove', function(event) {{
                    const tooltip = d3.select('#tooltip');
                    // 使用clientX/clientY，因为tooltip是fixed定位，相对于视口
                    // 让tooltip紧贴光标
                    const offset = 8;
                    tooltip.style('left', (event.clientX + offset) + 'px')
                           .style('top', (event.clientY + offset) + 'px');
                }})
                .on('click', function(event, d) {{
                    showCompanyDetail(d.data.name);
                }});
            
            // Company name to domain mapping for logos
            const companyDomains = {{
                'Amazon': 'amazon.com',
                'Meta': 'meta.com',
                'Microsoft': 'microsoft.com',
                'TCS': 'tcs.com',
                'Google': 'google.com',
                'Apple': 'apple.com',
                'Cognizant': 'cognizant.com',
                'Walmart': 'walmart.com',
                'Deloitte': 'deloitte.com',
                'JPMorgan Chase': 'jpmorgan.com',
                'Infosys': 'infosys.com',
                'Oracle': 'oracle.com',
                'EY': 'ey.com',
                'HCL': 'hcl.com',
                'Capgemini': 'capgemini.com',
                'Intel': 'intel.com',
                'Cisco': 'cisco.com',
                'IBM': 'ibm.com',
                'Accenture': 'accenture.com',
                'NVIDIA': 'nvidia.com',
                'Wipro': 'wipro.com',
                'Fidelity': 'fidelity.com',
                'Fidelity Investments': 'fidelity.com',
                'Salesforce': 'salesforce.com',
                'LTIMindtree': 'ltimindtree.com',
                'Citibank': 'citi.com',
                'Qualcomm': 'qualcomm.com',
                'Tech Mahindra': 'techmahindra.com',
                'Tesla': 'tesla.com',
                'Goldman Sachs': 'goldmansachs.com',
                'PayPal': 'paypal.com',
                'Compunnel': 'compunnel.com',
                'LinkedIn': 'linkedin.com',
                'L&T Infotech': 'lntinfotech.com',
                'PwC': 'pwc.com',
                'Uber': 'uber.com',
                'AWS': 'amazon.com',
                'Syntel': 'syntelinc.com',
                'Randstad': 'randstad.com',
                'CGI': 'cgi.com',
                'Cummins': 'cummins.com',
                'Hexaware': 'hexaware.com',
                'L&T Technology Services': 'ltts.com',
                'Mindtree': 'mindtree.com',
                'UST': 'ust.com',
                'KPMG': 'kpmg.com',
                'IGATE': 'igate.com'
            }};
            
            // Add content to cells
            cells.each(function(d) {{
                const cell = d3.select(this);
                const cellWidth = d.x1 - d.x0;
                const cellHeight = d.y1 - d.y0;
                const minSize = Math.min(cellWidth, cellHeight);
                
                // Get logo URL using Clearbit Logo API
                const domain = companyDomains[d.data.name] || d.data.name.toLowerCase().replace(/\\s+/g, '') + '.com';
                const logoUrl = `https://logo.clearbit.com/${{domain}}`;
                
                // 调整显示逻辑：增大logo和数字，同时保持小方框的自适应
                // Logo大小：增大比例和最大限制，但保持动态调整
                const logoSize = Math.min(Math.min(cellWidth, cellHeight) * 0.22, 50);  // 增大logo：从15%到22%，最大从30px到50px
                // 根据格子大小动态调整字号，增大默认值但保持自适应
                const nameFontSize = Math.max(7, Math.min(Math.min(cellWidth, cellHeight) * 0.07, 11));  // 公司名称：最小7px，最大11px
                const valueFontSize = Math.max(9, Math.min(Math.min(cellWidth, cellHeight) * 0.08, 16));  // 数值：最小9px，最大16px（增大）
                const rankFontSize = Math.max(8, Math.min(Math.min(cellWidth, cellHeight) * 0.06, 11));  // 排名：最小8px，最大11px
                
                let content = '<div class="cell-content">';
                content += '<div class="cell-header">';
                content += `<span class="cell-rank" style="font-size: ${{rankFontSize}}px;">#${{d.data.rank}}</span>`;
                if (d.data.is_icc) {{
                    content += '<span class="cell-icc-badge">ICC</span>';
                }}
                content += '</div>';
                
                // 降低显示阈值，让更多信息可以显示
                const showName = minSize > 30;  // 从50降低到30
                const showValue = minSize > 35;  // 从60降低到35
                
                content += `<div class="cell-logo-container">`;
                content += `<img class="cell-logo" src="${{logoUrl}}" alt="${{d.data.name}}" style="max-width: ${{logoSize}}px; max-height: ${{logoSize}}px;" onerror="this.style.display='none'; const fallback = this.nextElementSibling; if (fallback) fallback.style.display='block';">`;
                // Show company name below logo (or as fallback if logo fails)
                if (showName) {{
                    content += `<div class="cell-company-name" style="font-size: ${{nameFontSize}}px;">${{d.data.name}}</div>`;
                }} else {{
                    // Fallback name if logo fails and cell is too small (initially hidden)
                    content += `<div class="cell-company-name" style="font-size: ${{nameFontSize}}px; display: none; font-weight: bold; background: rgba(255, 255, 255, 0.9); padding: 2px 4px; border-radius: 3px;">${{d.data.name}}</div>`;
                }}
                content += `</div>`;
                
                // 显示数值（降低阈值）
                if (showValue) {{
                    content += `<div class="cell-value" style="font-size: ${{valueFontSize}}px;">${{d.data.beneficiaries.toLocaleString()}}</div>`;
                }}
                
                // Show rank change only for ICC companies (显示在右下角)
                if (d.data.is_icc && d.data.rank_change_direction) {{
                    const arrow = d.data.rank_change_direction === 'up' ? '↑' : '↓';
                    const changeClass = d.data.rank_change_direction;
                    content += `<div class="cell-change ${{changeClass}}"><span class="cell-change-arrow">${{arrow}}</span><span>${{d.data.rank_change_value}}</span></div>`;
                }}
                
                content += '</div>';
                cell.html(content);
            }});
        }}
        
        // 页面加载时创建初始热力图
        createTreemap();
        
        // 公司名称映射表（处理不同年份名称差异）
        const companyNameMapping = {{
            'AWS': 'AMAZON',
            'Amazon': 'AMAZON',
            'Fidelity': 'FIDELITY TECHNOLOGY GROUP LLC D B A FIDELITY INVESTMENTS',
            'Fidelity Investments': 'FIDELITY TECHNOLOGY GROUP LLC D B A FIDELITY INVESTMENTS'
        }};
        
        // 显示公司详情页面
        function showCompanyDetail(companyName) {{
            // 获取当前点击的公司数据，用于获取全名
            let clickedCompany = null;
            for (const year of availableYears) {{
                if (allYearsData[year]) {{
                    clickedCompany = allYearsData[year].find(c => c.name === companyName);
                    if (clickedCompany) break;
                }}
            }}
            
            if (!clickedCompany) {{
                alert('未找到该公司数据');
                return;
            }}
            
            // 使用全名进行匹配（更稳定）
            const fullName = clickedCompany.full_name.toUpperCase();
            
            // 收集该公司历年的数据
            const companyHistory = [];
            const sortedYears = availableYears.slice().sort((a, b) => a - b); // 正序（从早到晚）
            
            sortedYears.forEach(year => {{
                if (allYearsData[year]) {{
                    // 先尝试用全名匹配
                    let company = allYearsData[year].find(c => c.full_name.toUpperCase() === fullName);
                    // 如果找不到，尝试用名称匹配（处理名称映射）
                    if (!company) {{
                        const mappedName = companyNameMapping[companyName];
                        if (mappedName) {{
                            company = allYearsData[year].find(c => 
                                c.name === companyName || 
                                c.full_name.toUpperCase() === mappedName ||
                                c.name === mappedName
                            );
                        }} else {{
                            company = allYearsData[year].find(c => c.name === companyName);
                        }}
                    }}
                    
                    if (company) {{
                        companyHistory.push({{
                            year: year,
                            beneficiaries: company.beneficiaries,
                            rank: company.rank,
                            is_icc: company.is_icc
                        }});
                    }}
                }}
            }});
            
            if (companyHistory.length === 0) {{
                alert('未找到该公司的历史数据');
                return;
            }}
            
            // 显示模态框
            const modal = document.getElementById('company-modal');
            const modalTitle = document.getElementById('modal-company-name');
            const chartTitle = document.getElementById('modal-chart-title');
            modalTitle.textContent = companyName;
            chartTitle.textContent = companyName + '历年H1B申请通过数';
            modal.classList.add('show');
            
            // 创建柱状图
            createCompanyChart(companyHistory);
        }}
        
        // 关闭模态框
        function closeModal() {{
            document.getElementById('company-modal').classList.remove('show');
        }}
        
        // 创建公司历年数据柱状图
        function createCompanyChart(data) {{
            // 清除旧图表
            d3.select('#company-chart').selectAll('*').remove();
            
            const margin = {{top: 40, right: 40, bottom: 100, left: 80}}; // 增加底部边距以容纳X轴标签
            const width = 800 - margin.left - margin.right;
            const height = 500 - margin.top - margin.bottom;
            
            const svg = d3.select('#company-chart')
                .append('svg')
                .attr('width', width + margin.left + margin.right)
                .attr('height', height + margin.top + margin.bottom);
            
            const g = svg.append('g')
                .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
            
            // X轴：年份（正序，从早到晚）
            const sortedData = data.slice().sort((a, b) => a.year - b.year);
            const xScale = d3.scaleBand()
                .domain(sortedData.map(d => d.year))
                .range([0, width])
                .padding(0.2);
            
            // Y轴：Beneficiaries数量
            const maxBeneficiaries = d3.max(sortedData, d => d.beneficiaries);
            const yScale = d3.scaleLinear()
                .domain([0, maxBeneficiaries * 1.1])
                .range([height, 0]);
            
            // 添加X轴
            g.append('g')
                .attr('transform', `translate(0,${{height}})`)
                .call(d3.axisBottom(xScale))
                .selectAll('text')
                .style('text-anchor', 'middle')
                .attr('class', 'chart-axis');
            
            // 添加X轴标签
            g.append('text')
                .attr('x', width / 2)
                .attr('y', height + 50)
                .attr('class', 'chart-label')
                .style('text-anchor', 'middle')
                .style('font-size', '12px')
                .text('历年公司排名 | H1B employer 排行榜');
            
            // 添加Y轴
            g.append('g')
                .call(d3.axisLeft(yScale).tickFormat(d => d.toLocaleString()))
                .attr('class', 'chart-axis');
            
            // 添加Y轴标签
            g.append('text')
                .attr('transform', 'rotate(-90)')
                .attr('y', -60)
                .attr('x', -height / 2)
                .attr('class', 'chart-label')
                .style('text-anchor', 'middle')
                .text('H1B申请通过数');
            
            // 添加柱状图（先绘制，这样折线会在上方）
            g.selectAll('.chart-bar')
                .data(sortedData)
                .enter()
                .append('rect')
                .attr('class', 'chart-bar')
                .attr('x', d => xScale(d.year))
                .attr('y', d => yScale(d.beneficiaries))
                .attr('width', xScale.bandwidth())
                .attr('height', d => height - yScale(d.beneficiaries))
                .attr('fill', d => d.is_icc ? '#9EBA83' : '#9EBA83')
                .on('mouseenter', function(event, d) {{
                    d3.select(this).attr('opacity', 0.7);
                    const tooltip = d3.select('#tooltip');
                    tooltip.html(`
                        <strong>${{d.year}}</strong><br>
                        H1B申请通过数: ${{d.beneficiaries.toLocaleString()}}<br>
                        Rank: #${{d.rank}}
                    `);
                    tooltip.classed('show', true);
                }})
                .on('mouseleave', function() {{
                    d3.select(this).attr('opacity', 1);
                    d3.select('#tooltip').classed('show', false);
                }})
                .on('mousemove', function(event) {{
                    const tooltip = d3.select('#tooltip');
                    // 使用clientX/clientY，因为tooltip是fixed定位，相对于视口
                    // 让tooltip紧贴光标
                    const offset = 8;
                    tooltip.style('left', (event.clientX + offset) + 'px')
                           .style('top', (event.clientY + offset) + 'px');
                }});
            
            // 添加折线（在柱状图上方，往上移动更多避免和数字重合）
            const lineOffset = 25; // 从10px改为25px，往上移动更多
            const line = d3.line()
                .x(d => xScale(d.year) + xScale.bandwidth() / 2)
                .y(d => yScale(d.beneficiaries) - lineOffset) // 在柱子上方25px
                .curve(d3.curveMonotoneX);
            
            g.append('path')
                .datum(sortedData)
                .attr('fill', 'none')
                .attr('stroke', '#9EBA83')
                .attr('stroke-width', 2)
                .attr('d', line);
            
            // 添加折线上的点
            g.selectAll('.line-point')
                .data(sortedData)
                .enter()
                .append('circle')
                .attr('cx', d => xScale(d.year) + xScale.bandwidth() / 2)
                .attr('cy', d => yScale(d.beneficiaries) - lineOffset)
                .attr('r', 4)
                .attr('fill', '#9EBA83')
                .attr('stroke', 'white')
                .attr('stroke-width', 2);
            
            // 在最后一个点（最近的年份）添加箭头
            if (sortedData.length > 0) {{
                const lastPoint = sortedData[sortedData.length - 1];
                const secondLastPoint = sortedData.length > 1 ? sortedData[sortedData.length - 2] : null;
                
                if (secondLastPoint) {{
                    const x1 = xScale(secondLastPoint.year) + xScale.bandwidth() / 2;
                    const y1 = yScale(secondLastPoint.beneficiaries) - lineOffset;
                    const x2 = xScale(lastPoint.year) + xScale.bandwidth() / 2;
                    const y2 = yScale(lastPoint.beneficiaries) - lineOffset;
                    
                    // 计算箭头角度
                    const angle = Math.atan2(y2 - y1, x2 - x1);
                    const arrowLength = 10;
                    const arrowAngle = Math.PI / 6;
                    
                    // 绘制箭头
                    const arrowPath = `M ${{x2}} ${{y2}} L ${{x2 - arrowLength * Math.cos(angle - arrowAngle)}} ${{y2 - arrowLength * Math.sin(angle - arrowAngle)}} M ${{x2}} ${{y2}} L ${{x2 - arrowLength * Math.cos(angle + arrowAngle)}} ${{y2 - arrowLength * Math.sin(angle + arrowAngle)}}`;
                    
                    g.append('path')
                        .attr('d', arrowPath)
                        .attr('stroke', '#9EBA83')
                        .attr('stroke-width', 2)
                        .attr('fill', 'none')
                        .attr('stroke-linecap', 'round');
                }}
            }}
            
            // 在柱子上方显示数值（如果柱子足够高）
            g.selectAll('.bar-value')
                .data(sortedData)
                .enter()
                .append('text')
                .attr('class', 'chart-label')
                .attr('x', d => xScale(d.year) + xScale.bandwidth() / 2)
                .attr('y', d => {{
                    const barHeight = height - yScale(d.beneficiaries);
                    // 如果柱子高度小于30px，将标签放在柱子内部顶部
                    return barHeight < 30 ? yScale(d.beneficiaries) + 15 : yScale(d.beneficiaries) - 5;
                }})
                .attr('text-anchor', 'middle')
                .attr('fill', d => {{
                    const barHeight = height - yScale(d.beneficiaries);
                    return barHeight < 30 ? '#fff' : '#666';
                }})
                .style('font-weight', d => {{
                    const barHeight = height - yScale(d.beneficiaries);
                    return barHeight < 30 ? 'bold' : 'normal';
                }})
                .text(d => d.beneficiaries.toLocaleString());
            
            // 在柱子下方显示排名（往下调整，避免和年份重合）
            g.selectAll('.bar-rank')
                .data(sortedData)
                .enter()
                .append('text')
                .attr('class', 'chart-label')
                .attr('x', d => xScale(d.year) + xScale.bandwidth() / 2)
                .attr('y', height + 35)  // 从20改为35，往下调整
                .attr('text-anchor', 'middle')
                .style('font-weight', 'bold')
                .text(d => `Rank #${{d.rank}}`);
        }}
        
        // 点击模态框外部关闭
        window.onclick = function(event) {{
            const modal = document.getElementById('company-modal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
    </script>
</body>
</html>
"""
    
    return html_content

def main():
    # 项目目录
    project_dir = Path('/Users/ziling/Desktop/Lawgent-Infographics')
    output_path = project_dir / 'heatmap.html'
    
    # 读取所有年份的数据（2016-2025）
    all_years_data = {}
    years = list(range(2016, 2026))  # 2016到2025
    
    for year in years:
        csv_path = project_dir / f'{year}_data.csv'
        if csv_path.exists():
            print(f"Reading {year} CSV from: {csv_path}")
            companies = read_csv_data(csv_path, year=year)
            if companies:
                all_years_data[year] = companies
                print(f"Found {len(companies)} companies for {year}")
        else:
            print(f"Warning: {year} CSV not found at {csv_path}")
    
    if not all_years_data:
        print("❌ Error: No data found for any year!")
        return
    
    print(f"\n✅ Successfully loaded data for {len(all_years_data)} year(s): {sorted(all_years_data.keys())}")
    
    print("Generating heatmap HTML...")
    html_content = generate_heatmap_html(all_years_data)
    
    print(f"Writing HTML to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Heatmap generated successfully!")
    print(f"Open {output_path} in your browser to view the heatmap.")

if __name__ == '__main__':
    main()

