import sys, os
import re

def get_html_template(content_html):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LTTD Whipsaw & Lagging Exit Investigation Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            color: #f8fafc;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
        }}
        .glass-card {{
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px rgba(255, 255, 255, 0.08) solid;
            border-radius: 1rem;
        }}
        .accent-gradient {{
            background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        pre {{
            background: #0b0f19 !important;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            border: 1px rgba(255, 255, 255, 0.05) solid;
        }}
        code {{
            font-family: 'Fira Code', 'Courier New', Courier, monospace;
            color: #f43f5e;
            background: rgba(0,0,0,0.2);
            padding: 0.1rem 0.3rem;
            border-radius: 0.25rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px rgba(255, 255, 255, 0.08) solid;
            text-align: left;
        }}
        th {{
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
            font-weight: 600;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
    </style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-5xl mx-auto space-y-8">
        <!-- Header Card -->
        <div class="glass-card p-8 flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
            <div>
                <p class="text-sm font-semibold tracking-wider uppercase text-violet-400">LTTD Quant System</p>
                <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight mt-1">
                    <span class="accent-gradient">Whipsaw & Exit Lag</span> Investigation
                </h1>
                <p class="text-slate-400 text-sm mt-2">Quantitative analysis of trade delays on Jan 2017, Feb 2021, and Oct 2021</p>
            </div>
            <div class="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                <div class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <span class="text-xs font-semibold text-emerald-400">Investigation Complete</span>
            </div>
        </div>

        <!-- Main Content -->
        <div class="glass-card p-8 space-y-6 prose prose-invert max-w-none">
            {content_html}
        </div>
        
        <!-- Footer -->
        <div class="text-center text-xs text-slate-500 mt-8">
            <p>LTTD Quant Trading System • Generated in Real-time</p>
        </div>
    </div>
</body>
</html>
"""

def md_to_html(md_text):
    html_lines = []
    in_table = False
    in_list = False
    
    for line in md_text.split('\n'):
        # Keep leading whitespace for indentation checks if needed, but strip for clean processing
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</tbody></table></div>")
                in_table = False
            continue
            
        # Headers
        if stripped.startswith("# "):
            html_lines.append(f"<h1 class='text-2xl font-bold mt-8 mb-4 text-white border-b border-slate-700 pb-2'>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2 class='text-xl font-bold mt-6 mb-3 text-violet-300'>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3 class='text-lg font-bold mt-4 mb-2 text-slate-200'>{stripped[4:]}</h3>")
            
        # Lists
        elif stripped.startswith("* ") or stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul class='list-disc pl-6 my-3 text-slate-300 space-y-2'>")
                in_list = True
            content = stripped[2:]
            # Inline formatting
            content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
            content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="text-blue-400 hover:underline">\1</a>', content)
            html_lines.append(f"<li>{content}</li>")
            
        # Tables
        elif stripped.startswith("|"):
            if "---" in stripped:
                continue # Skip table divider
            if not in_table:
                html_lines.append("<div class='overflow-x-auto my-4'><table class='min-w-full text-slate-300'>")
                in_table = True
                
            parts = [p.strip() for p in stripped.split("|")[1:-1]]
            if len(parts) > 0:
                # Check if it's the header row (has table tag directly before)
                is_first_row = html_lines[-1].endswith("<table class='min-w-full text-slate-300'>")
                if is_first_row:
                    html_lines.append("<thead><tr>" + "".join(f"<th>{p}</th>" for p in parts) + "</tr></thead><tbody>")
                else:
                    html_lines.append("<tr>" + "".join(f"<td>{p}</td>" for p in parts) + "</tr>")
                    
        # Normal text
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</tbody></table></div>")
                in_table = False
                
            # Inline formatting
            content = stripped
            content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
            content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="text-blue-400 hover:underline">\1</a>', content)
            html_lines.append(f"<p class='my-3 text-slate-300 leading-relaxed'>{content}</p>")
            
    # Close any unclosed tags
    if in_list:
        html_lines.append("</ul>")
    if in_table:
        html_lines.append("</tbody></table></div>")
        
    return "\n".join(html_lines)

def main():
    report_path = "/home/lutfizain/.gemini/antigravity-cli/brain/2a9de974-25ee-44f7-a510-bfaa35808fb1/whipsaw_investigation_report.md"
    if not os.path.exists(report_path):
        print(f"Error: report path {report_path} does not exist.")
        return
        
    with open(report_path, "r") as f:
        md_text = f.read()
        
    # Convert markdown to HTML using our standalone function
    content_html = md_to_html(md_text)
    
    # Build complete HTML string
    full_html = get_html_template(content_html)
    
    # Save to tmp/whipsaw_investigation_report.html
    out_path = "/run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system/tmp/whipsaw_investigation_report.html"
    with open(out_path, "w") as f:
        f.write(full_html)
        
    print(f"Generated beautiful HTML report at: {out_path}")

if __name__ == "__main__":
    main()
