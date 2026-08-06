"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";

type Props = {
  children: string;
  className?: string;
  /** Compact mode for bullets / citations */
  compact?: boolean;
};

const components: Components = {
  p: ({ children }) => <p className="md-p">{children}</p>,
  strong: ({ children }) => <strong className="md-strong">{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  ul: ({ children }) => <ul className="md-list">{children}</ul>,
  ol: ({ children }) => <ol className="md-list md-list-ordered">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  h1: ({ children }) => <h3 className="md-heading">{children}</h3>,
  h2: ({ children }) => <h3 className="md-heading">{children}</h3>,
  h3: ({ children }) => <h4 className="md-heading">{children}</h4>,
  h4: ({ children }) => <h4 className="md-heading">{children}</h4>,
  code: ({ children, className }) => {
    const inline = !className;
    if (inline) {
      return <code className="md-code">{children}</code>;
    }
    return (
      <pre className="md-pre">
        <code>{children}</code>
      </pre>
    );
  },
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="md-link">
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="md-quote">{children}</blockquote>
  ),
  hr: () => <hr className="md-hr" />,
};

export function MarkdownBody({ children, className, compact }: Props) {
  const text = (children || "").trim();
  if (!text) return null;
  return (
    <div
      className={`md-body${compact ? " md-body-compact" : ""}${
        className ? ` ${className}` : ""
      }`}
    >
      <ReactMarkdown components={components}>{text}</ReactMarkdown>
    </div>
  );
}
