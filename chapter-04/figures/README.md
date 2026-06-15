# Chapter 4 figures

Source and exported files for the diagrams used in Chapter 4. These are the
editable originals for the production/editorial team (Packt prefers diagram
sources it can redraw, plus high-resolution exports).

| Figure | Files | Description |
|---|---|---|
| Figure 4.1 | `figure-4-1-rag-pipeline.{mmd,svg,png}` | The six components of a RAG pipeline (offline indexing + online answering) |
| Figure 4.2 | `figure-4-2-mcp.{mmd,svg,png}` | MCP roles: AI host / MCP client / MCP server / live cluster |

- `.mmd` — [Mermaid](https://mermaid.js.org/) source (the editable original).
- `.svg` — vector export (scales to any size; preferred for print).
- `.png` — raster export rendered at high scale for inline use.

## Regenerating

```bash
npx @mermaid-js/mermaid-cli -i figure-4-1-rag-pipeline.mmd \
  -o figure-4-1-rag-pipeline.png -c mermaid-config.json -b white -s 4
```

> Naming note: Packt assigns a book code and numbers figures as `B<code>_04_01.png`.
> Rename these to that scheme when the book code is known.
