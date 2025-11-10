#!/usr/bin/env python3
"""
Generate an interactive heatmap visualization for H1B sponsor data
"""

import csv
import re
from pathlib import Path

def parse_number(value):
    """Parse number with commas"""
    if not value or value == '':
        return 0
    return int(value.replace(',', ''))

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

def read_csv_data(csv_path):
    """Read and parse CSV data"""
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows or summary rows
            if not row.get('rank') or not row.get('简称 Employer (Petitioner) Name'):
                continue
            
            rank = row.get('rank', '').strip()
            if not rank.isdigit():
                continue
            
            is_icc = row.get('是否ICC', '').strip() == 'Y'
            name = row.get('简称 Employer (Petitioner) Name', '').strip()
            full_name = row.get('全名 Employer (Petitioner) Name', '').strip()
            beneficiaries = parse_number(row.get('Beneficiaries Approved', '0'))
            rank_change = row.get('排名变化', '').strip()
            
            direction, change = parse_ranking_change(rank_change)
            
            companies.append({
                'rank': int(rank),
                'is_icc': is_icc,
                'name': name,
                'full_name': full_name,
                'beneficiaries': beneficiaries,
                'rank_change_direction': direction,
                'rank_change_value': change
            })
    
    return companies

def generate_heatmap_html(companies):
    """Generate HTML treemap heatmap where size is proportional to beneficiaries"""
    
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
        'Fidelity Investments': '#0171BB',
        'Salesforce': '#00A1E0',
        'LTIMindtree': '#0066CC',
        'Citibank': '#0066CC',
        'Qualcomm': '#3253DC',
        'Tech Mahindra': '#C72E2E',
        'Tesla': '#E31937',
        'Goldman Sachs': '#000000',
        'PayPal': '#003087'
    }
    
    # Also create a mapping for case-insensitive lookup
    brand_colors_lower = {k.lower(): v for k, v in brand_colors.items()}
    
    # Sort by beneficiaries (descending) for treemap
    companies_sorted = sorted(companies, key=lambda x: x['beneficiaries'], reverse=True)
    
    # Prepare JSON data for JavaScript with brand colors
    import json
    companies_json = json.dumps([
        {
            'name': c['name'],
            'full_name': c['full_name'],
            'beneficiaries': c['beneficiaries'],
            'rank': c['rank'],
            'is_icc': c['is_icc'],
            'rank_change_direction': c['rank_change_direction'],
            'rank_change_value': c['rank_change_value'],
            'brand_color': brand_colors.get(c['name'], brand_colors_lower.get(c['name'].lower(), '#666666'))  # Default gray if not found
        }
        for c in companies_sorted
    ], ensure_ascii=False)
    
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
            padding: 8px;
        }}
        
        .treemap-cell:hover {{
            border-color: rgba(0, 0, 0, 0.3);
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        .treemap-cell.icc {{
            border-color: #ff6b6b;
            border-width: 3px;
        }}
        
        .cell-content {{
            display: flex;
            flex-direction: column;
            height: 100%;
        }}
        
        .cell-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }}
        
        .cell-rank {{
            font-size: 0.75em;
            font-weight: bold;
            opacity: 0.9;
        }}
        
        .cell-icc-badge {{
            background: #ff6b6b;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 0.65em;
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
            font-size: 1.1em;
            font-weight: bold;
            margin-top: auto;
        }}
        
        .cell-change {{
            font-size: 0.7em;
            margin-top: 2px;
        }}
        
        .cell-change.up {{
            color: #27ae60;
        }}
        
        .cell-change.down {{
            color: #e74c3c;
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
            color: #667eea;
        }}
        
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 H1B Sponsor Company Heatmap</h1>
        <p class="subtitle">Top 30 Companies by H1B Beneficiaries Approved (Size = Number of Beneficiaries)</p>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{len(companies)}</div>
                <div class="stat-label">Companies</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{sum(c['beneficiaries'] for c in companies):,}</div>
                <div class="stat-label">Total Beneficiaries</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{len([c for c in companies if c['is_icc']])}</div>
                <div class="stat-label">ICC Companies</div>
            </div>
        </div>
        
        <div id="treemap"></div>
        
        <div class="legend">
            <div class="legend-item">
                <div style="border: 2px solid #ff6b6b; padding: 2px 6px; border-radius: 4px;">ICC</div>
                <span>ICC Company</span>
            </div>
            <div class="legend-item">
                <span style="color: #666; font-size: 0.9em;">Colors represent company brand colors</span>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        const companies = {companies_json};
        
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
            .style('color', d => getTextColor(d.data.brand_color))
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
                tooltip.style('left', (event.pageX - tooltip.node().offsetWidth / 2) + 'px')
                       .style('top', (event.pageY - tooltip.node().offsetHeight - 10) + 'px');
            }});
        
        // Add content to cells
        cells.each(function(d) {{
            const cell = d3.select(this);
            const cellWidth = d.x1 - d.x0;
            const cellHeight = d.y1 - d.y0;
            const minSize = Math.min(cellWidth, cellHeight);
            
            let content = '<div class="cell-content">';
            content += '<div class="cell-header">';
            content += `<span class="cell-rank">#${{d.data.rank}}</span>`;
            if (d.data.is_icc) {{
                content += '<span class="cell-icc-badge">ICC</span>';
            }}
            content += '</div>';
            
            // Only show name if cell is large enough
            if (minSize > 80) {{
                content += `<div class="cell-name">${{d.data.name}}</div>`;
            }}
            
            // Only show value if cell is large enough
            if (minSize > 60) {{
                content += `<div class="cell-value">${{d.data.beneficiaries.toLocaleString()}}</div>`;
            }}
            
            // Show rank change if available and cell is large enough
            if (d.data.rank_change_direction && minSize > 100) {{
                const arrow = d.data.rank_change_direction === 'up' ? '⬆️' : '⬇️';
                const changeClass = d.data.rank_change_direction;
                content += `<div class="cell-change ${{changeClass}}">${{arrow}} ${{d.data.rank_change_value}}</div>`;
            }}
            
            content += '</div>';
            cell.html(content);
        }});
    </script>
</body>
</html>
"""
    
    return html_content

def main():
    csv_path = Path('/Users/kathy/Downloads/Trump上台前后 H1B sponsor中ICC公司数量对比 - clean_2025年top30.csv')
    output_path = Path('/Users/kathy/H1B_Company_Heatmap/heatmap.html')
    
    print(f"Reading CSV from: {csv_path}")
    companies = read_csv_data(csv_path)
    print(f"Found {len(companies)} companies")
    
    print("Generating heatmap HTML...")
    html_content = generate_heatmap_html(companies)
    
    print(f"Writing HTML to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Heatmap generated successfully!")
    print(f"Open {output_path} in your browser to view the heatmap.")

if __name__ == '__main__':
    main()

