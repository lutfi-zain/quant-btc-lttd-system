import re
import os

def markdown_to_html(md_text):
    # Basic markdown parsing for HTML presentation
    md_text = re.sub(r'^### (.*?)$', r'<h3 class="text-lg font-semibold text-teal-400 mt-6 mb-2">\1</h3>', md_text, flags=re.M)
    md_text = re.sub(r'^## (.*?)$', r'<h2 class="text-xl font-bold text-teal-350 mt-8 mb-4 border-b border-gray-750 pb-2">\1</h2>', md_text, flags=re.M)
    md_text = re.sub(r'^# (.*?)$', r'<h1 class="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-emerald-400 mb-6">\1</h1>', md_text, flags=re.M)
    
    md_text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-teal-200 font-semibold">\1</strong>', md_text)
    md_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" class="text-teal-400 hover:underline" target="_blank">\1</a>', md_text)
    
    md_text = re.sub(r'```(python|bash|json)?\n(.*?)\n```', r'<pre class="bg-gray-900 border border-gray-800 rounded-lg p-4 font-mono text-sm overflow-x-auto text-teal-350 my-4">\2</pre>', md_text, flags=re.DOTALL)
    md_text = re.sub(r'`(.*?)`', r'<code class="bg-gray-900 px-1.5 py-0.5 rounded font-mono text-sm text-emerald-400 border border-gray-800">\1</code>', md_text)
    
    md_text = re.sub(r'^\s*-\s+(.*?)$', r'<li class="ml-4 list-disc text-gray-300 mb-1">\1</li>', md_text, flags=re.M)
    md_text = re.sub(r'^\s*\*\s+(.*?)$', r'<li class="ml-4 list-disc text-gray-300 mb-1">\1</li>', md_text, flags=re.M)
    md_text = re.sub(r'^\s*\d+\.\s+(.*?)$', r'<li class="ml-4 list-decimal text-gray-300 mb-1">\1</li>', md_text, flags=re.M)
    
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
            "NOTE": "border-blue-500 bg-blue-950/20 text-blue-200",
            "TIP": "border-emerald-500 bg-emerald-950/20 text-emerald-200",
            "IMPORTANT": "border-purple-500 bg-purple-950/20 text-purple-200",
            "WARNING": "border-amber-500 bg-amber-950/20 text-amber-200",
            "CAUTION": "border-red-500 bg-red-950/20 text-red-200"
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
    
    md_text = re.sub(r'\$\$(.*?)\$\$', r'<div class="bg-gray-900/50 text-center font-mono py-3 rounded-lg border border-gray-800 my-4 text-teal-350 font-bold">\1</div>', md_text, flags=re.DOTALL)
    md_text = re.sub(r'\$(.*?)\$', r'<code class="font-mono bg-gray-900 px-1 py-0.5 rounded text-teal-350 font-bold">\1</code>', md_text)

    table_pattern = re.compile(r'(^\|.*?\|\s*$\n?)+', re.M)
    
    def parse_table(match):
        table_text = match.group(0)
        lines = [line.strip() for line in table_text.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            return table_text
            
        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
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
                cell_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-teal-300">\1</strong>', cell)
                html += f'<td class="px-4 py-3 whitespace-nowrap">{cell_formatted}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        return html
        
    md_text = table_pattern.sub(parse_table, md_text)
    
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
    report_file = "/home/lutfizain/.gemini/antigravity-cli/brain/2a9de974-25ee-44f7-a510-bfaa35808fb1/noise_reduction_report.md"
    
    with open(report_file, 'r') as f:
        md_text = f.read()
        
    content_html = markdown_to_html(md_text)
    
    template = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LTTD Noise Reduction & Performance Optimization Report</title>
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
    
    <header class="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div class="max-w-4xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <span class="px-2.5 py-1 rounded bg-teal-500/10 border border-teal-500/30 text-teal-400 font-mono text-xs font-bold uppercase tracking-wider">Performance Audit</span>
                    <span class="text-gray-500 text-xs">V3.0 (Optimized)</span>
                </div>
                <h1 class="text-2xl font-black text-white mt-1.5 tracking-tight flex items-center gap-2">
                    <span class="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 via-emerald-400 to-cyan-400">LTTD Noise Reduction Report</span>
                </h1>
            </div>
            <div class="text-right">
                <div class="text-xs text-gray-500">Target Metric</div>
                <div class="font-mono text-teal-400 font-bold text-sm">CAGR 84.78% / Sharpe 1.56</div>
            </div>
        </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-10 bg-gray-900/30 border border-gray-850/60 rounded-3xl my-8 shadow-2xl backdrop-blur">
        {content_html}
    </main>

</body>
</html>
"""
    
    output_html = "/run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/tmp/noise_reduction_report.html"
    with open(output_html, 'w') as f:
        f.write(template)
    print(f"Generated HTML report at: {output_html}")

if __name__ == '__main__':
    main()
