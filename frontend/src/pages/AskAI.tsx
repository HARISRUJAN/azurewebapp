import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { searchAPI } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    content: string;
    document_title: string;
    document_source: string;
    document_url?: string;
    chunk_index: number;
  }>;
}

export const AskAI: React.FC = () => {
  const location = useLocation();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasProcessedInitialQuestion = useRef(false);

  // Deduplicate citations based on document_title and document_source
  const deduplicateCitations = useCallback((citations: Message['citations']) => {
    if (!citations || citations.length === 0) return [];
    
    const seen = new Set<string>();
    const unique: typeof citations = [];
    
    for (const citation of citations) {
      const key = `${citation.document_title}|${citation.document_source}`;
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(citation);
      }
    }
    
    return unique;
  }, []);

  const handleQuery = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: query,
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setIsLoading(true);

    try {
      const response = await searchAPI.query(query);
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.answer,
        citations: deduplicateCitations(response.citations),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Search API error:', error);
      const errorDetails = error?.response?.data?.detail || error?.message || 'Unknown error';
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error while processing your question: ${errorDetails}. Please try again.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, deduplicateCitations]);

  // Handle initial question from navigation (only once)
  useEffect(() => {
    const initialQuestion = location.state?.initialQuestion;
    if (initialQuestion && !hasProcessedInitialQuestion.current) {
      hasProcessedInitialQuestion.current = true;
      setQuestion(initialQuestion);
      handleQuery(initialQuestion);
    }
  }, [location.state, handleQuery]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoading && question.trim()) {
      handleQuery(question);
    }
  };

  // Markdown table styling component
  const markdownComponents: any = {
    table: ({ children }: { children?: React.ReactNode }) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse border border-secondary-300 rounded-lg">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: { children?: React.ReactNode }) => (
      <thead className="bg-secondary-100">{children}</thead>
    ),
    tbody: ({ children }: { children?: React.ReactNode }) => (
      <tbody>{children}</tbody>
    ),
    tr: ({ children }: { children?: React.ReactNode }) => (
      <tr className="border-b border-secondary-200 hover:bg-secondary-50">{children}</tr>
    ),
    th: ({ children }: { children?: React.ReactNode }) => (
      <th className="px-4 py-3 text-left font-semibold text-secondary-900 border border-secondary-300">
        {children}
      </th>
    ),
    td: ({ children }: { children?: React.ReactNode }) => (
      <td className="px-4 py-3 text-secondary-700 border border-secondary-300">
        {children}
      </td>
    ),
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="mb-4 leading-relaxed">{children}</p>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => (
      <strong className="font-semibold text-secondary-900">{children}</strong>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="list-disc list-inside mb-4 space-y-2">{children}</ul>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
      <ol className="list-decimal list-inside mb-4 space-y-2">{children}</ol>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="ml-4">{children}</li>
    ),
    code: ({ children, className }: { children?: React.ReactNode; className?: string }) => {
      const isInline = !className;
      return isInline ? (
        <code className="bg-secondary-100 px-1.5 py-0.5 rounded text-sm font-mono text-secondary-900">
          {children}
        </code>
      ) : (
        <code className="block bg-secondary-100 p-4 rounded-lg overflow-x-auto text-sm font-mono text-secondary-900">
          {children}
        </code>
      );
    },
  };

  return (
    <div 
      className="min-h-screen bg-gradient-to-br from-secondary-50 via-white to-primary-50 flex items-center justify-center px-4 py-12"
      style={{ fontFamily: "'Montserrat', sans-serif" }}
    >
      <div className="max-w-5xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl lg:text-5xl font-bold text-secondary-900" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            Ask AI about Governance
          </h1>
          <p className="text-lg text-secondary-600">
            Get answers about AI regulations and governance frameworks
          </p>
        </div>

        {/* Chat Container - Centered and Spacious */}
        <div className="bg-white rounded-2xl shadow-xl flex flex-col h-[600px] border border-secondary-100">
          <div className="p-8 space-y-6 overflow-y-auto flex-1">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-4">
                  <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  </div>
                  <p className="text-xl text-secondary-600 font-medium">
                    Start a conversation by asking a question about AI governance.
                  </p>
                  <p className="text-secondary-500">
                    Try asking about regulations, frameworks, or best practices.
                  </p>
                </div>
              </div>
            )}
            
            {messages.map((message, idx) => {
              const uniqueCitations = deduplicateCitations(message.citations);

              return (
                <div
                  key={`${message.role}-${idx}-${message.content.substring(0, 20)}`}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
                >
                  <div
                    className={`max-w-3xl rounded-2xl p-6 shadow-md transition-all duration-300 ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white rounded-br-none'
                        : 'bg-secondary-50 text-secondary-900 rounded-bl-none border border-secondary-200'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown components={markdownComponents}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap leading-relaxed text-base">{message.content}</p>
                    )}
                    
                    {uniqueCitations && uniqueCitations.length > 0 && (
                      <div className={`mt-6 pt-6 border-t ${message.role === 'user' ? 'border-primary-400' : 'border-secondary-300'}`}>
                        <p className={`text-sm font-semibold mb-3 ${message.role === 'user' ? 'text-primary-100' : 'text-secondary-700'}`}>
                          Sources:
                        </p>
                        <ul className="space-y-3">
                          {uniqueCitations.map((citation, cIdx) => (
                            <li key={`${citation.document_title}-${citation.document_source}-${cIdx}`} className="text-sm">
                              <span className={`font-medium ${message.role === 'user' ? 'text-white' : 'text-secondary-900'}`}>
                                {citation.document_title}
                              </span>
                              {citation.document_source && (
                                <span className={message.role === 'user' ? 'text-primary-200' : 'text-secondary-600'}>
                                  {' '}({citation.document_source})
                                </span>
                              )}
                              {citation.document_url && (
                                <a
                                  href={citation.document_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`ml-2 font-medium hover:underline ${
                                    message.role === 'user' ? 'text-primary-200 hover:text-white' : 'text-primary-600 hover:text-primary-700'
                                  }`}
                                >
                                  View source →
                                </a>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            
            {isLoading && (
              <div className="flex justify-start animate-fade-in">
                <div className="bg-secondary-100 rounded-2xl rounded-bl-none p-6 border border-secondary-200">
                  <div className="flex items-center space-x-3">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <p className="text-secondary-600 font-medium">Thinking...</p>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Form - Enhanced */}
        <form onSubmit={handleSubmit} className="flex gap-4 bg-white rounded-2xl shadow-xl p-6 border border-secondary-100">
          <Input
            placeholder="Ask a question about AI governance..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1 text-lg py-4 px-6 rounded-xl border-2 border-secondary-200 focus:border-primary-500 transition-colors"
            disabled={isLoading}
          />
          <Button 
            type="submit" 
            disabled={isLoading || !question.trim()}
            className="px-8 py-4 text-lg font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </Button>
        </form>
      </div>
    </div>
  );
};
