###
# scripts/search.py — PubMed 文獻搜尋腳本
# 用途：透過 PubMed E-utilities API 搜尋文獻，輸出標題與摘要
# 輸入：搜尋關鍵字（命令列參數），可選 --max 指定回傳數量
# 輸出：stdout 印出搜尋結果（PMID、標題、摘要）
# 關聯：被 SKILL.md 引用，LLM 透過 bash tool 執行
###

import argparse
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


def search_pubmed(query: str, max_results: int = 5) -> list[dict]:
    """搜尋 PubMed 並回傳文獻列表"""
    # Step 1: esearch 取得 PMID 列表
    encoded_query = urllib.parse.quote(query)
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={encoded_query}&retmax={max_results}&sort=date&retmode=json"
    )
    with urllib.request.urlopen(search_url, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    id_list = data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    # Step 2: efetch 取得文獻詳細資料
    ids_str = ",".join(id_list)
    fetch_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={ids_str}&rettype=abstract&retmode=xml"
    )
    with urllib.request.urlopen(fetch_url, timeout=15) as resp:
        xml_data = resp.read().decode()

    # Step 3: 解析 XML
    root = ET.fromstring(xml_data)
    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="N/A")
        title = article.findtext(".//ArticleTitle", default="N/A")
        abstract = article.findtext(".//AbstractText", default="（無摘要）")
        results.append({"pmid": pmid, "title": title, "abstract": abstract})

    return results


def main():
    parser = argparse.ArgumentParser(description="搜尋 PubMed 文獻")
    parser.add_argument("query", help="搜尋關鍵字")
    parser.add_argument("--max", type=int, default=5, help="回傳最大筆數（預設 5）")
    args = parser.parse_args()

    results = search_pubmed(args.query, args.max)

    if not results:
        print(f"找不到與 '{args.query}' 相關的文獻")
        return

    print(f"搜尋 '{args.query}'，找到 {len(results)} 筆結果：\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] PMID: {r['pmid']}")
        print(f"    標題: {r['title']}")
        abstract_preview = r["abstract"][:200]
        if len(r["abstract"]) > 200:
            abstract_preview += "..."
        print(f"    摘要: {abstract_preview}")
        print()


if __name__ == "__main__":
    main()
