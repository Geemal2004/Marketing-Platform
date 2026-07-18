'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import clsx from 'clsx';

type MarkdownContentProps = {
    content: string;
    className?: string;
};

/**
 * Normalize common LLM markdown quirks into cleaner CommonMark.
 * e.g. a lone line "**1. Scenes**" becomes "## 1. Scenes"
 */
function normalizeLlmMarkdown(raw: string): string {
    const text = (raw || '').replace(/\r\n/g, '\n').trim();
    if (!text) return '';

    return text
        .split('\n')
        .map((line) => {
            const trimmed = line.trim();

            // **1. Scenes** or **Scenes:** → heading
            const boldSection = trimmed.match(/^\*\*(.+?)\*\*:?\s*$/);
            if (boldSection) {
                return `\n## ${boldSection[1].replace(/:$/, '')}\n`;
            }

            // 1. SCENES: or 1. Scenes — standalone label line (no other prose)
            const numberedLabel = trimmed.match(/^(\d+)\.\s+([A-Z][A-Za-z0-9 /&-]{1,60}):?\s*$/);
            if (numberedLabel) {
                return `\n## ${numberedLabel[1]}. ${numberedLabel[2]}\n`;
            }

            return line;
        })
        .join('\n')
        .replace(/\n{3,}/g, '\n\n');
}

/**
 * Renders VLM / analysis markdown as styled HTML.
 */
export default function MarkdownContent({ content, className }: MarkdownContentProps) {
    const markdown = normalizeLlmMarkdown(content);

    return (
        <div className={clsx('markdown-content text-[#4b5563] text-[15px] leading-relaxed', className)}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    h1: ({ children }) => (
                        <h1 className="text-xl font-bold text-[#111827] mt-5 mb-2 first:mt-0 tracking-tight">
                            {children}
                        </h1>
                    ),
                    h2: ({ children }) => (
                        <h2 className="text-lg font-semibold text-[#111827] mt-5 mb-2 first:mt-0 border-b border-[#e5e7eb] pb-1.5">
                            {children}
                        </h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="text-base font-semibold text-[#1f2937] mt-4 mb-1.5 first:mt-0">
                            {children}
                        </h3>
                    ),
                    h4: ({ children }) => (
                        <h4 className="text-[15px] font-semibold text-[#374151] mt-3 mb-1 first:mt-0">
                            {children}
                        </h4>
                    ),
                    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                    strong: ({ children }) => (
                        <strong className="font-semibold text-[#111827]">{children}</strong>
                    ),
                    em: ({ children }) => <em className="italic text-[#374151]">{children}</em>,
                    ul: ({ children }) => (
                        <ul className="mb-3 last:mb-0 space-y-1.5 list-disc pl-5 marker:text-[#00897f]">
                            {children}
                        </ul>
                    ),
                    ol: ({ children }) => (
                        <ol className="mb-3 last:mb-0 space-y-1.5 list-decimal pl-5 marker:text-[#00897f] marker:font-semibold">
                            {children}
                        </ol>
                    ),
                    li: ({ children }) => <li className="pl-0.5 leading-relaxed">{children}</li>,
                    blockquote: ({ children }) => (
                        <blockquote className="mb-3 last:mb-0 border-l-2 border-[#00897f]/40 pl-3 py-0.5 text-[#6b7280] italic">
                            {children}
                        </blockquote>
                    ),
                    hr: () => <hr className="my-4 border-[#e5e7eb]" />,
                    a: ({ href, children }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#00897f] underline underline-offset-2 hover:text-[#007a71]"
                        >
                            {children}
                        </a>
                    ),
                    code: ({ className: codeClassName, children }) => {
                        const isBlock = Boolean(codeClassName);
                        if (isBlock) {
                            return (
                                <code className="block text-[13px] font-mono text-[#1f2937] whitespace-pre">
                                    {children}
                                </code>
                            );
                        }
                        return (
                            <code className="rounded bg-[#f3f4f6] px-1.5 py-0.5 text-[13px] font-mono text-[#1f2937]">
                                {children}
                            </code>
                        );
                    },
                    pre: ({ children }) => (
                        <pre className="mb-3 last:mb-0 overflow-x-auto rounded-md border border-[#e5e7eb] bg-[#f9fafb] p-3">
                            {children}
                        </pre>
                    ),
                    table: ({ children }) => (
                        <div className="mb-3 last:mb-0 overflow-x-auto rounded-md border border-[#e5e7eb]">
                            <table className="w-full text-left text-sm">{children}</table>
                        </div>
                    ),
                    thead: ({ children }) => (
                        <thead className="bg-[#f9fafb] border-b border-[#e5e7eb]">{children}</thead>
                    ),
                    th: ({ children }) => (
                        <th className="px-3 py-2 font-semibold text-[#111827]">{children}</th>
                    ),
                    td: ({ children }) => (
                        <td className="px-3 py-2 border-t border-[#e5e7eb] text-[#4b5563]">{children}</td>
                    ),
                }}
            >
                {markdown}
            </ReactMarkdown>
        </div>
    );
}
