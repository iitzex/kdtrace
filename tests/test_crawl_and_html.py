from crawl import Crawler
from gen_html import HtmlGenerator


def test_crawler_skips_malformed_tse_rows(monkeypatch, tmp_path):
    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "stat": "OK",
                "tables": [{}, {}, {}, {}, {}, {}, {}, {}, {
                    "data": [
                        ["1101", "台泥", "12,345,000", "1,234", "678,900", "45", "46", "44", "45.5", "+", "0.5"],
                        ["ABCD", "壞資料", "1,000", "1", "2,000", "--", "2", "1", "1.5", "+", "0.1"],
                    ]
                }],
            }

    monkeypatch.setattr("crawl.get_request", lambda url: DummyResponse())
    crawler = Crawler()
    crawler.recorder.prefix = str(tmp_path)
    crawler.fetch_tse_data("2024-01-02")

    out = tmp_path / "1101.csv"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "2024-01-02" in content
    assert "ABCD" not in content


def test_html_generator_writes_report(tmp_path, monkeypatch):
    (tmp_path / "sample.csv").write_text("1101,台泥\n----,divider\n2330,台積電\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    generator = HtmlGenerator(output_dir=str(tmp_path))
    generator.generate("sample")

    output = tmp_path / "sample.html"
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "1101" in text
    assert "2330" in text
    assert "pic/1101.png" in text
