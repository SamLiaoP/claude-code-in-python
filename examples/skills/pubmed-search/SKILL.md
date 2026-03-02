---
name: pubmed-search
description: 當需要搜尋 PubMed 醫學文獻、查詢臨床試驗時使用
allowed-tools: "bash,python,read_file"
---

## 使用時機
- 搜尋醫學論文、查詢臨床試驗資料
- 查找特定疾病或藥物相關文獻

## 步驟
1. 用 `bash` 執行現成腳本：`python ./scripts/search.py "搜尋關鍵字"`
2. 解析輸出結果，整理成結構化摘要回報給使用者

如需了解 API 細節（例如進階參數、回傳格式），用 `read_file` 讀取 `./references/api_guide.md`。

## 可用資源

| 路徑 | 說明 |
|---|---|
| `./scripts/search.py` | 可直接執行的搜尋腳本，接受關鍵字參數 |
| `./references/api_guide.md` | PubMed E-utilities API 參考文件 |

## 快速範例

```bash
# 搜尋 "cancer treatment" 最新 5 篇文獻
python ./scripts/search.py "cancer treatment"

# 搜尋並指定回傳數量
python ./scripts/search.py "statins cardiovascular" --max 10
```
