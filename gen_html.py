import logging
import os
from util import get_list

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HtmlGenerator:
    """Generates visual stock reports in HTML format with a premium look."""

    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir

    def _get_styles(self) -> str:
        """Returns the base CSS styles for the report."""
        return """
        <style>
            :root {
                --bg-color: #f1f5f9;
                --card-bg: #ffffff;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --accent: #0284c7;
                --accent-hover: #0369a1;
                --border: #e2e8f0;
            }
            body {
                font-family: 'Inter', -apple-system, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                width: 80%;
                max-width: 2560px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                color: var(--accent);
                font-size: 2.5rem;
                margin-bottom: 40px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .stock-card {
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 0;
                overflow: hidden;
                margin-bottom: 40px;
                box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
                transition: transform 0.2s, border-color 0.2s;
            }
            .stock-card:hover {
                transform: translateY(-4px);
                border-color: var(--accent);
            }
            .stock-header-info {
                padding: 20px 24px;
            }
            .stock-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border);
                padding-bottom: 15px;
                margin-bottom: 15px;
            }
            .stock-title {
                font-size: 1.5rem;
                font-weight: 700;
            }
            .stock-id {
                color: var(--accent);
                margin-right: 10px;
            }
            .links {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-bottom: 20px;
            }
            .links a {
                color: var(--text-secondary);
                text-decoration: none;
                font-size: 0.9rem;
                padding: 6px 12px;
                border-radius: 6px;
                background: var(--bg-color);
                border: 1px solid var(--border);
                transition: all 0.2s;
            }
            .links a:hover {
                color: var(--text-primary);
                background: var(--accent);
                border-color: var(--accent);
            }
            .chart-container {
                display: flex;
                justify-content: center;
                background: #fff;
                border-radius: 8px;
                padding: 10px;
                overflow: hidden;
            }
            .chart-container img {
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }
            .divider {
                height: 4px;
                background: linear-gradient(90deg, transparent, var(--accent), transparent);
                margin: 50px 0;
                border: none;
            }
            @media (max-width: 768px) {
                .stock-header {
                    flex-direction: column;
                    align-items: flex-start;
                }
            }
        </style>
        """

    def generate(self, name: str):
        """Generates an HTML report for the given stock list name."""
        file_path = os.path.join(self.output_dir, f"{name}.html")
        logging.info(f"Generating premium HTML report for {name.upper()} -> {file_path}")
        
        stocks = get_list(name)
        if not stocks:
            logging.warning(f"No stocks found for {name}. Skipping HTML generation.")
            return

        html_content = []
        html_content.append(f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name.upper()} 股市分析報表</title>
    {self._get_styles()}
</head>
<body>
    <div class="container">
        <h1>{name.upper()} Market Report</h1>
""")

        for sid, title in stocks:
            if "-" in sid:
                html_content.append('<hr class="divider">')
                continue

            html_content.append(f"""
        <div class="stock-card">
            <div class="stock-header-info">
                <div class="stock-header">
                    <div class="stock-title"><span class="stock-id">{sid}</span>{title}</div>
                </div>
                <div class="links">
                    <a href="https://www.cnyes.com/twstock/{sid}" target="_blank">CNYES</a>
                    <a href="https://statementdog.com/analysis/{sid}" target="_blank">財報狗</a>
                    <a href="https://www.wantgoo.com/stock/{sid}" target="_blank">玩股網</a>
                    <a href="https://goodinfo.tw/StockInfo/StockDetail.asp?STOCK_ID={sid}" target="_blank">Goodinfo</a>
                    <a href="https://histock.tw/stock/{sid}" target="_blank">HiStock</a>
                    <a href="https://www.fugle.tw/ai/{sid}" target="_blank">Fugle</a>
                    <a href="www/{sid}.html">Local Report</a>
                </div>
            </div>
            <div class="chart-container">
                <img src="pic/{sid}.png" alt="{title} Chart" loading="lazy">
            </div>
        </div>
""")

        html_content.append("""
    </div>
</body>
</html>
""")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(html_content)
            logging.info(f"Successfully generated {file_path}")
        except Exception as e:
            logging.error(f"Failed to write HTML report: {e}")

def html_generator():
    """Convenience function for backward compatibility."""
    generator = HtmlGenerator()
    generator.generate("tse")

if __name__ == "__main__":
    html_generator()
