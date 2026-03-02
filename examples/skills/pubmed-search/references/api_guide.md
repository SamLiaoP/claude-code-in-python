# PubMed E-utilities API 參考

## Base URL

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## 常用 Endpoint

### esearch.fcgi — 搜尋

搜尋 PubMed 資料庫，回傳符合條件的 PMID 列表。

| 參數 | 說明 | 範例 |
|---|---|---|
| `db` | 資料庫名稱 | `pubmed` |
| `term` | 搜尋關鍵字，支援布林運算 | `cancer AND treatment` |
| `retmax` | 回傳最大筆數（預設 20） | `5` |
| `sort` | 排序方式 | `date`、`relevance` |
| `retmode` | 回傳格式 | `xml`（預設）、`json` |

**範例 URL：**
```
esearch.fcgi?db=pubmed&term=statins+cardiovascular&retmax=5&sort=date&retmode=json
```

**JSON 回傳結構：**
```json
{
  "esearchresult": {
    "count": "12345",
    "retmax": "5",
    "idlist": ["39000001", "39000002", "39000003"]
  }
}
```

### efetch.fcgi — 取得文獻詳細資料

用 PMID 取得完整文獻資料（標題、作者、摘要等）。

| 參數 | 說明 | 範例 |
|---|---|---|
| `db` | 資料庫名稱 | `pubmed` |
| `id` | PMID，多筆用逗號分隔 | `39000001,39000002` |
| `rettype` | 回傳類型 | `abstract`、`medline` |
| `retmode` | 回傳格式 | `xml`（預設）、`text` |

**XML 回傳結構（簡化）：**
```xml
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>39000001</PMID>
      <Article>
        <ArticleTitle>文章標題</ArticleTitle>
        <Abstract>
          <AbstractText>摘要內容...</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Wang</LastName><ForeName>Wei</ForeName></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
```

## 注意事項

- **頻率限制**：無 API Key 時最多 3 次/秒，有 API Key 可到 10 次/秒
- **API Key 申請**：https://www.ncbi.nlm.nih.gov/account/settings/ 的 API Key Management
- **帶 API Key 的方式**：URL 加上 `&api_key=YOUR_KEY`
