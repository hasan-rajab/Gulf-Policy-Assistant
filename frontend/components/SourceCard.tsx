import { Source } from "@/lib/types";
import { isArabic } from "@/lib/language";

export default function SourceCard({ source }: { source: Source }) {
  const rerank = source.metadata?.retrieval?.rerank_score;
  const classification = source.metadata?.classification;

  return (
    <details className="sourceCard">
      <summary>
        <span className="sourceTag">{source.source_id}</span>
        <span className="sourceTitle">{source.title}</span>
        <span className="sourceScore">{Math.round(source.score * 100)}% evidence</span>
      </summary>
      <div className="sourceMeta">
        {source.page ? `Page ${source.page}` : `Chunk ${source.chunk_index + 1}`}
        {source.source_uri ? ` · ${source.source_uri}` : ""}
        {classification ? ` · ${classification}` : ""}
        {typeof rerank === "number" ? ` · rerank ${Math.round(rerank * 100)}%` : ""}
      </div>
      <p dir={isArabic(source.text) ? "rtl" : "ltr"}>{source.text}</p>
    </details>
  );
}
