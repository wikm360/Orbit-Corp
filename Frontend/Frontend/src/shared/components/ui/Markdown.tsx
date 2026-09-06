import type { Root } from "hast";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { visit } from "unist-util-visit";

// The LLM sometimes wraps supplementary content in raw <details>/<summary>
// HTML (not just markdown), so raw HTML needs to be parsed (rehypeRaw) and
// then sanitized (rehypeSanitize) rather than escaped or dropped.
const schema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "details", "summary"],
};

// The model never emits the `open` attribute, so every <details> renders
// collapsed by default (native HTML behavior) - requiring an extra click to
// see content that's often the actual answer. Force them all open instead.
function rehypeForceDetailsOpen() {
  return (tree: Root) => {
    visit(tree, "element", (node) => {
      if (node.tagName === "details") {
        node.properties.open = true;
      }
    });
  };
}

export function Markdown({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none break-words prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-table:my-2">
      <div className="overflow-x-auto">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw, [rehypeSanitize, schema], rehypeForceDetailsOpen]}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
