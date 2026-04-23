from pathlib import Path

import pandas as pd

from main import AnalysisResult, AnalysisService, AppPaths, ReportService, StockAnalyzer


class DummyFetcher:
    def __init__(self):
        idx = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"])
        self.revenue = pd.DataFrame({"revenue": [10, 11, 12, 13], "revenueYOY": [1, 2, 3, 4]}, index=idx)
        self.eps = pd.DataFrame({"eps": [1.0, 1.1, 1.2, 1.3], "epsYOY": [5, 6, 7, 8]}, index=idx)
        self.profitability = pd.DataFrame(
            {"grossMargin": [1, 2, 3, 4], "operatingMargin": [1, 2, 3, 4], "profitMargin": [1, 2, 3, 4]},
            index=idx,
        )
        self.investors = pd.DataFrame(
            {"foreignVolume": [1, 2, 3, 4], "totalVolume": [5, 6, 7, 8]},
            index=idx,
        )

    def get_revenue(self, sid):
        return self.revenue

    def get_eps(self, sid):
        return self.eps

    def get_profitability(self, sid):
        return self.profitability

    def get_investors(self, sid):
        return self.investors

    def get_price(self, sid):
        return 123.4


class DummyVisualizer:
    def __init__(self):
        self.calls = []

    def draw_report(self, result, output_path):
        self.calls.append((result, output_path))
        Path(output_path).write_text("ok", encoding="utf-8")
        return 0.01, 0.02


def test_stock_analyzer_single_stock_smoke(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (tmp_path / "json").mkdir()
    (data_dir / "1101.csv").write_text(
        "date,amount,volume,open,high,low,close,diff,number\n"
        "2024-01-02,100,1000,10,11,9,10.5,0.5,50\n"
        "2024-01-03,200,2000,10.5,11.5,10,11,0.5,70\n",
        encoding="utf-8",
    )

    fetcher = DummyFetcher()
    visualizer = DummyVisualizer()
    analyzer = StockAnalyzer(fetcher, visualizer, force=True)

    timings = analyzer.analyze_stock(("1101", "台泥"))

    assert timings is not None
    assert set(["read_csv", "fetch_phase", "indicators", "plot", "savefig"]).issubset(timings)
    assert len(visualizer.calls) == 1
    result, output_path = visualizer.calls[0]
    assert isinstance(result, AnalysisResult)
    assert result.sid == "1101"
    assert result.title == "台泥"
    assert output_path.endswith("pic/1101.png")
    assert (tmp_path / "pic" / "1101.png").exists()


def test_analysis_service_and_report_service_smoke(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "json").mkdir()
    (tmp_path / "tse.csv").write_text("1101,台泥\n", encoding="utf-8")
    ((tmp_path / "data") / "1101.csv").write_text(
        "date,amount,volume,open,high,low,close,diff,number\n"
        "2024-01-02,100,1000,10,11,9,10.5,0.5,50\n"
        "2024-01-03,200,2000,10.5,11.5,10,11,0.5,70\n",
        encoding="utf-8",
    )

    analyzer = StockAnalyzer(DummyFetcher(), DummyVisualizer(), force=True, paths=AppPaths())
    service = AnalysisService(analyzer, paths=AppPaths())
    report_service = ReportService(stock_list_name="sample")

    stocks = service.get_stocks()
    assert stocks == [("1101", "台泥")]

    service.run_batch(stocks, cores=1)
    (tmp_path / "sample.csv").write_text("1101,台泥\n", encoding="utf-8")
    report_service.generate_main_report()

    assert (tmp_path / "sample.html").exists()
