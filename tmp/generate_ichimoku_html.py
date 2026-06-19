import re
import os

def markdown_to_html(md_text):
    # Basic markdown parsing for HTML presentation
    # Convert headers
    md_text = re.sub(r'^### (.*?)$', r'<h3 class="text-lg font-semibold text-teal-400 mt-6 mb-2">\1</h3>', md_text, flags=re.M)
    md_text = re.sub(r'^## (.*?)$', r'<h2 class="text-xl font-bold text-teal-350 mt-8 mb-4 border-b border-gray-750 pb-2">\1</h2>', md_text, flags=re.M)
    md_text = re.sub(r'^# (.*?)$', r'<h1 class="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-emerald-400 mb-6">\1</h1>', md_text, flags=re.M)
    
    # Convert bold
    md_text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-teal-200 font-semibold">\1</strong>', md_text)
    
    # Convert links
    md_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" class="text-teal-400 hover:underline" target="_blank">\1</a>', md_text)
    
    # Convert code blocks
    md_text = re.sub(r'```(python|bash|json)?\n(.*?)\n```', r'<pre class="bg-gray-900 border border-gray-800 rounded-lg p-4 font-mono text-sm overflow-x-auto text-teal-350 my-4">\2</pre>', md_text, flags=re.DOTALL)
    
    # Convert inline code
    md_text = re.sub(r'`(.*?)`', r'<code class="bg-gray-900 px-1.5 py-0.5 rounded font-mono text-sm text-emerald-400 border border-gray-800">\1</code>', md_text)
    
    # Convert lists
    # First, list items
    md_text = re.sub(r'^\s*-\s+(.*?)$', r'<li class="ml-4 list-disc text-gray-300 mb-1">\1</li>', md_text, flags=re.M)
    md_text = re.sub(r'^\s*\d+\.\s+(.*?)$', r'<li class="ml-4 list-decimal text-gray-300 mb-1">\1</li>', md_text, flags=re.M)
    
    # Convert blockquotes (Alerts)
    def parse_alert(match):
        content = match.group(1)
        alert_type = "NOTE"
        if "[!NOTE]" in content:
            alert_type = "NOTE"
            content = content.replace("[!NOTE]", "").strip()
        elif "[!TIP]" in content:
            alert_type = "TIP"
            content = content.replace("[!TIP]", "").strip()
        elif "[!IMPORTANT]" in content:
            alert_type = "IMPORTANT"
            content = content.replace("[!IMPORTANT]", "").strip()
        elif "[!WARNING]" in content:
            alert_type = "WARNING"
            content = content.replace("[!WARNING]", "").strip()
        elif "[!CAUTION]" in content:
            alert_type = "CAUTION"
            content = content.replace("[!CAUTION]", "").strip()
            
        colors = {
            "NOTE": "border-blue-500 bg-blue-950/20 text-blue-205",
            "TIP": "border-emerald-500 bg-emerald-950/20 text-emerald-205",
            "IMPORTANT": "border-purple-500 bg-purple-950/20 text-purple-205",
            "WARNING": "border-amber-500 bg-amber-950/20 text-amber-205",
            "CAUTION": "border-red-500 bg-red-950/20 text-red-205"
        }
        
        headers = {
            "NOTE": "💡 NOTE",
            "TIP": "🚀 TIP",
            "IMPORTANT": "⚠️ IMPORTANT",
            "WARNING": "🔥 WARNING",
            "CAUTION": "🚫 CAUTION"
        }
        
        return f'<div class="border-l-4 p-4 rounded-r-lg my-4 {colors[alert_type]}"><p class="font-bold text-xs uppercase tracking-wider mb-1">{headers[alert_type]}</p><p>{content}</p></div>'
        
    md_text = re.compile(r'^>\s+(.*?)(?=\n[^>]|\Z)', re.M | re.S).sub(parse_alert, md_text)
    
    # Convert math equations (LaTeX style)
    md_text = re.sub(r'\$\$(.*?)\$\$', r'<div class="bg-gray-900/50 text-center font-mono py-3 rounded-lg border border-gray-800 my-4 text-teal-350 font-bold">\1</div>', md_text, flags=re.DOTALL)
    md_text = re.sub(r'\$(.*?)\$', r'<code class="font-mono bg-gray-900 px-1 py-0.5 rounded text-teal-350 font-bold">\1</code>', md_text)

    # Convert tables
    # Find all table blocks
    table_pattern = re.compile(r'(^\|.*?\|\s*$\n?)+', re.M)
    
    def parse_table(match):
        table_text = match.group(0)
        lines = [line.strip() for line in table_text.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            return table_text
            
        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
        # Skip line 1 (the separator line: |---|---|)
        rows_data = []
        for r_line in lines[2:]:
            cells = [c.strip() for c in r_line.split('|')[1:-1]]
            rows_data.append(cells)
            
        html = '<div class="overflow-x-auto my-6 border border-gray-800 rounded-lg bg-gray-900/30">'
        html += '<table class="min-w-full divide-y divide-gray-800 text-left text-sm">'
        html += '<thead class="bg-gray-900/80 text-teal-400 font-semibold">'
        html += '<tr>'
        for h in headers:
            html += f'<th class="px-4 py-3 border-b border-gray-800">{h}</th>'
        html += '</tr>'
        html += '</thead>'
        html += '<tbody class="divide-y divide-gray-850 text-gray-300">'
        for idx, row in enumerate(rows_data):
            bg_cls = "bg-gray-900/10" if idx % 2 == 1 else "bg-gray-900/30"
            html += f'<tr class="{bg_cls} hover:bg-teal-950/20 transition-colors">'
            for cell in row:
                # Check for bold or colors in cells
                cell_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-teal-300">\1</strong>', cell)
                html += f'<td class="px-4 py-3 whitespace-nowrap">{cell_formatted}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        return html
        
    md_text = table_pattern.sub(parse_table, md_text)
    
    # Wrap loose paragraph lines that are not part of other tags
    paragraphs = []
    lines = md_text.split('\n')
    in_list = False
    list_html = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                paragraphs.append(list_html)
                list_html = ""
                in_list = False
            continue
            
        if stripped.startswith('<li') or stripped.startswith('<ul') or stripped.startswith('<ol'):
            if not in_list:
                in_list = True
                list_html = '<ul class="space-y-1.5 my-3 pl-2">'
            list_html += line + "\n"
        elif in_list and not (stripped.startswith('<li') or stripped.startswith('</ul') or stripped.startswith('</ol')):
            list_html += '</ul>'
            paragraphs.append(list_html)
            list_html = ""
            in_list = False
            
        if not in_list:
            if stripped.startswith('<h') or stripped.startswith('<div') or stripped.startswith('<pre') or stripped.startswith('<table') or stripped.startswith('<a') or stripped.startswith('<p') or stripped.startswith('</'):
                paragraphs.append(line)
            else:
                paragraphs.append(f'<p class="text-gray-300 leading-relaxed mb-4">{line}</p>')
                
    if in_list:
        list_html += '</ul>'
        paragraphs.append(list_html)
        
    return '\n'.join(paragraphs)

def main():
    workspace_root = "/run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system"
    tmp_dir = os.path.join(workspace_root, "tmp")
    
    research_file = os.path.join(tmp_dir, "ichimoku_quant_research.md")
    boolean_file = os.path.join(tmp_dir, "ichimoku_boolean_edges.md")
    statistical_file = os.path.join(tmp_dir, "ichimoku_statistical_edges.md")
    combination_file = os.path.join(tmp_dir, "ichimoku_combination_edges.md")
    
    # Read files
    research_md = ""
    if os.path.exists(research_file):
        with open(research_file, 'r') as f:
            research_md = f.read()
            
    boolean_md = ""
    if os.path.exists(boolean_file):
        with open(boolean_file, 'r') as f:
            boolean_md = f.read()
            
    statistical_md = ""
    if os.path.exists(statistical_file):
        with open(statistical_file, 'r') as f:
            statistical_md = f.read()
            
    combination_md = ""
    if os.path.exists(combination_file):
        with open(combination_file, 'r') as f:
            combination_md = f.read()
            
    # Process each to HTML
    research_html = markdown_to_html(research_md)
    boolean_html = markdown_to_html(boolean_md)
    statistical_html = markdown_to_html(statistical_md)
    combination_html = markdown_to_html(combination_md)
    
    # HTML Template
    template = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Ichimoku Quantitative Research Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    }},
                    colors: {{
                        gray: {{
                            850: '#1b2330',
                            900: '#0d131e',
                            950: '#060a12',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background: linear-gradient(135deg, #060a12 0%, #0d131e 100%);
        }}
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #060a12;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #1b2330;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #2b3a4a;
        }}
    </style>
</head>
<body class="text-gray-200 antialiased font-sans min-h-screen">
    
    <!-- Top Header -->
    <header class="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <span class="px-2.5 py-1 rounded bg-teal-500/10 border border-teal-500/30 text-teal-400 font-mono text-xs font-bold uppercase tracking-wider">Layer 1 & 2 Research</span>
                    <span class="text-gray-500 text-xs">V2.4</span>
                </div>
                <h1 class="text-2xl font-black text-white mt-1.5 tracking-tight flex items-center gap-2">
                    <span class="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 via-emerald-400 to-cyan-400">Ichimoku Cloud Quantitative Audit</span>
                </h1>
                <p class="text-gray-400 text-xs mt-1">Regime Classification, Causal Formulation & Mathematical Rigor on BTC-USD Daily History</p>
            </div>
            <div class="flex items-center gap-4 text-xs bg-gray-900 border border-gray-800 px-4 py-2.5 rounded-lg shadow-xl shadow-black/40">
                <div>
                    <div class="text-gray-500">Database Context</div>
                    <div class="font-mono text-teal-400 font-semibold">database/lttd.db</div>
                </div>
                <div class="w-px h-6 bg-gray-800"></div>
                <div>
                    <div class="text-gray-500">Last Synced</div>
                    <div class="font-mono text-teal-400 font-semibold">2026-06-19 17:22</div>
                </div>
            </div>
        </div>
    </header>

    <div class="max-w-7xl mx-auto px-6 py-8">
        
        <!-- Tab Navigation Buttons -->
        <div class="flex flex-wrap gap-2 mb-8 bg-gray-950/40 p-1.5 rounded-xl border border-gray-800/80 max-w-fit shadow-inner">
            <button onclick="switchTab('tab-research')" id="btn-tab-research" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 hover:text-white flex items-center gap-2 bg-teal-500/10 text-teal-400 border border-teal-500/20">
                📊 Mathematical & VIF Audit
            </button>
            <button onclick="switchTab('tab-causality')" id="btn-tab-causality" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 text-gray-400 hover:text-white flex items-center gap-2 border border-transparent">
                🛡️ Chikou & Causality
            </button>
            <button onclick="switchTab('tab-statistical')" id="btn-tab-statistical" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 text-gray-400 hover:text-white flex items-center gap-2 border border-transparent">
                📈 Single Strategy Backtests
            </button>
            <button onclick="switchTab('tab-combination')" id="btn-tab-combination" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 text-gray-400 hover:text-white flex items-center gap-2 border border-transparent">
                🧩 Boolean Combinations
            </button>
        </div>

        <!-- Main Content Area -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
            
            <!-- Left Sidebar (Always Visible Metrics Summary) -->
            <div class="lg:col-span-1 space-y-6">
                
                <!-- Performance Snapshot Card -->
                <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 shadow-xl backdrop-blur relative overflow-hidden group">
                    <div class="absolute -top-10 -right-10 w-24 h-24 bg-teal-500/10 rounded-full blur-xl group-hover:scale-150 transition-all duration-500"></div>
                    <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Baseline Comparison</h3>
                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between items-center text-xs text-gray-500">
                                <span>Buy & Hold CAGR</span>
                                <span class="font-mono text-gray-400">50.63%</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                                <div class="bg-gray-600 h-full rounded-full" style="width: 50%;"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between items-center text-xs text-gray-500">
                                <span>Best Single (Chikou Causal)</span>
                                <span class="font-mono text-teal-400 font-bold">64.77%</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                                <div class="bg-teal-500 h-full rounded-full" style="width: 64%;"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between items-center text-xs text-gray-500">
                                <span>Best Comb. (c3 & c6)</span>
                                <span class="font-mono text-emerald-400 font-bold">67.09%</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                                <div class="bg-emerald-400 h-full rounded-full" style="width: 67%;"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Integration Rules List Card -->
                <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 shadow-xl backdrop-blur">
                    <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Architecture Rules</h3>
                    <ul class="space-y-3.5 text-xs text-gray-300">
                        <li class="flex items-start gap-2.5">
                            <span class="text-teal-400 mt-0.5">✔</span>
                            <span><strong>Causal-Only</strong> Spans: Shift back calculation by 26 periods.</span>
                        </li>
                        <li class="flex items-start gap-2.5">
                            <span class="text-red-400 mt-0.5">✖</span>
                            <span><strong>No Traditional Chikou</strong>: Traditional Chikou has 26-period lookahead bias.</span>
                        </li>
                        <li class="flex items-start gap-2.5">
                            <span class="text-red-400 mt-0.5">✖</span>
                            <span><strong>Prune Collinear</strong>: Drop `price_cloud_top_diff` and `chikou_diff_causal` (VIF > 10).</span>
                        </li>
                        <li class="flex items-start gap-2.5">
                            <span class="text-teal-400 mt-0.5">✔</span>
                            <span><strong>Layer 1 Priority</strong>: Ideal as a regime filter, not a tactical trigger.</span>
                        </li>
                    </ul>
                </div>

                <!-- Diagnostic Metrics -->
                <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 shadow-xl backdrop-blur">
                    <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Model Recommendations</h3>
                    <div class="p-3 bg-teal-950/20 border border-teal-500/20 rounded-xl text-xs text-teal-300">
                        <span class="font-bold">Proposed Layer 1 Rule:</span>
                        <div class="font-mono bg-gray-950 p-2 rounded mt-1.5 border border-gray-800 text-[10px] overflow-x-auto text-emerald-400 select-all">
                            Bullish: Price > max(SA, SB) AND SA > SB
                            Bearish: Price < min(SA, SB) AND SA < SB
                        </div>
                    </div>
                </div>

            </div>

            <!-- Right Content Sections (Controlled by JS) -->
            <div class="lg:col-span-3 bg-gray-900/40 border border-gray-800/80 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur min-h-[60vh]">
                
                <!-- Tab 1: Mathematical & VIF Audit -->
                <div id="tab-research" class="tab-content block animate-fade-in">
                    {research_html}
                </div>

                <!-- Tab 2: Chikou & Causality -->
                <div id="tab-causality" class="tab-content hidden animate-fade-in">
                    {boolean_html}
                </div>

                <!-- Tab 3: Single Strategy Backtests -->
                <div id="tab-statistical" class="tab-content hidden animate-fade-in">
                    {statistical_html}
                </div>

                <!-- Tab 4: Boolean Combinations -->
                <div id="tab-combination" class="tab-content hidden animate-fade-in">
                    {combination_html}
                </div>

            </div>

        </div>

    </div>

    <!-- Script to handle switching tabs -->
    <script>
        function switchTab(tabId) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => {{
                content.classList.add('hidden');
                content.classList.remove('block');
            }});

            // Show current tab content
            const activeContent = document.getElementById(tabId);
            activeContent.classList.remove('hidden');
            activeContent.classList.add('block');

            // Reset all buttons styling
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach(btn => {{
                btn.className = "tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 text-gray-400 hover:text-white flex items-center gap-2 border border-transparent";
            }});

            // Style active button
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.className = "tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 hover:text-white flex items-center gap-2 bg-teal-500/10 text-teal-400 border border-teal-500/20";
        }}
    </script>

</body>
</html>
"""
    
    output_html_file = os.path.join(tmp_dir, "ichimoku_report.html")
    with open(output_html_file, 'w') as f:
        f.write(template)
        
    print(f"✓ Generated beautiful HTML report at: {output_html_file}")

if __name__ == '__main__':
    main()
