# documents

minecraft-pixelart の正本ドキュメント置き場。

## ドキュメントの読み方（トークン節約）

正本を広く読む前に、spacex_work の `calc/doc_graph.py` で節を絞る。

- グラフ: `spacex_work/cache/doc_graph_minecraft-pixelart.json`（走査対象はこの `documents/`）
- 例（spacex_work ルートから）: `python -B calc/doc_graph.py query "..." --graph cache/doc_graph_minecraft-pixelart.json --top 3`
- `--top 1` はヒントのみ。過信しない。既定は 3。
