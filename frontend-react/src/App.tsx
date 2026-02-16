import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Send, Bot, User, Database, Settings, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Toaster, toast } from 'sonner';
import Plot from 'react-plotly.js';
import { SettingsDialog } from './components/SettingsDialog';
import { LoginPage } from './components/LoginPage';
import { useAuth } from './contexts/AuthContext';

interface Message {
  role: 'user' | 'bot';
  content: string;
  sql?: string;
  data?: Record<string, unknown>[];
  chart?: { data: Record<string, unknown>[]; layout: Record<string, unknown> };
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function App() {
  const { t } = useTranslation();
  const { user, isLoading: isAuthLoading, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initialize welcome message with translation
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{ role: 'bot', content: t('app.welcome') }]);
    }
  }, [t, messages.length]);

  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Map messages to conversation_history format
      const history = messages.map(m => ({
        role: m.role === 'bot' ? 'assistant' : 'user',
        content: m.content
      }));

      const response = await axios.post(`${API_BASE_URL}/query/vanna`, {
        query: input,
        conversation_history: history
      }, { timeout: 120000 });

      if (response.data.success) {
        const botMsg: Message = {
          role: 'bot',
          content: response.data.explanation || t('app.query_executed') || 'Query executed.',
          sql: response.data.sql_query,
          data: response.data.data,
          chart: response.data.visualization_suggestion ? JSON.parse(response.data.visualization_suggestion) : null
        };
        setMessages(prev => [...prev, botMsg]);
      } else {
        toast.error(t('app.error_occurred') + ': ' + (response.data.error || 'Unknown error'));
        setMessages(prev => [...prev, { role: 'bot', content: t('app.error_occurred') + ': ' + (response.data.error || 'Unknown error') }]);
      }
    } catch (error: unknown) {
      console.error(error);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const axiosError = error as any;
      const errorMsg = axiosError.response?.data?.detail || axiosError.message || t('app.connection_failed');
      toast.error(errorMsg);
      setMessages(prev => [...prev, { role: 'bot', content: t('app.communication_error') + ': ' + errorMsg }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading spinner while verifying auth
  if (isAuthLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" />
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]" />
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]" />
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!user) {
    return (
      <>
        <LoginPage />
        <Toaster position="top-center" richColors />
      </>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm shrink-0">
        <div className="flex items-center space-x-2">
          <Database className="w-8 h-8 text-blue-600" />
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            {t('app.title')}
          </h1>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-500 mr-2 hidden sm:inline">
            {user.full_name || user.email || user.username}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSettingsOpen(true)}
            className="text-slate-500 hover:text-blue-600 hover:bg-blue-50"
          >
            <Settings className="w-6 h-6" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="text-slate-500 hover:text-red-600 hover:bg-red-50"
            title={t('auth.logout')}
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden flex flex-col max-w-5xl mx-auto w-full p-4 min-h-0">
        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          <div className="space-y-6 pb-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex space-x-3 max-w-[90%] ${m.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${m.role === 'user' ? 'bg-blue-600' : 'bg-slate-200'}`}>
                    {m.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-slate-600" />}
                  </div>
                  <div className="space-y-2 flex-1 min-w-0">
                    <Card className={m.role === 'user' ? 'bg-blue-600 text-white border-none shadow-md' : 'bg-white shadow-sm'}>
                      <CardContent className="p-3 text-sm whitespace-pre-wrap leading-relaxed">
                        {m.content}
                      </CardContent>
                    </Card>

                    {m.sql && (
                      <div className="bg-slate-900 rounded-lg p-3 overflow-x-auto shadow-inner border border-slate-700">
                        <p className="text-[10px] text-slate-400 mb-1 font-semibold uppercase tracking-wider flex items-center">
                          <Database className="w-3 h-3 mr-1" /> SQL Query
                        </p>
                        <code className="text-xs text-blue-300 font-mono break-all">{m.sql}</code>
                      </div>
                    )}

                    {m.chart && (
                      <div className="bg-white rounded-lg p-2 border shadow-md overflow-hidden min-h-[400px]">
                         <Plot
                           data={m.chart.data}
                           layout={{
                             ...m.chart.layout,
                             autosize: true,
                             width: undefined,
                             height: 400,
                             margin: { l: 50, r: 20, t: 30, b: 50 }
                           }}
                           style={{ width: "100%" }}
                           config={{ responsive: true, displayModeBar: false }}
                         />
                      </div>
                    )}

                    {m.data && m.data.length > 0 && !m.chart && (
                      <div className="bg-white rounded-lg border shadow-sm overflow-hidden mt-2">
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-xs text-left border-collapse">
                            <thead className="bg-slate-50 border-b">
                              <tr>
                                {Object.keys(m.data[0]).map(k => (
                                  <th key={k} className="px-3 py-2 font-semibold text-slate-600 border-r last:border-0">{k}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {m.data.slice(0, 10).map((row, ri) => (
                                <tr key={ri} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                                  {Object.values(row).map((v: unknown, vi) => (
                                    <td key={vi} className="px-3 py-2 text-slate-800 border-r last:border-0 truncate max-w-[200px]" title={String(v)}>
                                      {String(v)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          <div className="px-3 py-1.5 bg-slate-50 text-[10px] text-slate-500 flex justify-between items-center">
                            <span>{t('app.showing_rows', { current: Math.min(10, m.data.length), total: m.data.length })}</span>
                            {m.data.length > 10 && <span className="italic">{t('app.scroll_more')}</span>}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex space-x-3">
                  <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center animate-pulse">
                    <Bot className="w-5 h-5 text-slate-400" />
                  </div>
                  <div className="bg-white rounded-xl p-4 border shadow-sm flex items-center space-x-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="mt-4 flex space-x-2 p-2 bg-white rounded-2xl border shadow-xl ring-1 ring-black/5 shrink-0">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={t('app.placeholder')}
            className="flex-1 border-none focus-visible:ring-0 text-base py-6 bg-transparent"
            autoFocus
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()} className="h-12 px-6 rounded-xl shadow-lg bg-blue-600 hover:bg-blue-700 transition-all font-semibold">
            <Send className="w-5 h-5 mr-2" />
            {t('app.send')}
          </Button>
        </div>
      </main>
      <Toaster position="top-center" richColors />
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
    </div>
  );
}
