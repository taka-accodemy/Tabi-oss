import asyncio
import concurrent.futures
import logging
from typing import Dict, Any, List, Optional
from app.services.vanna_service import vanna_service, VannaNoSQLError
from app.core.config import settings

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Single-thread executor so all Vanna/ChromaDB (SQLite) calls happen on the
# same thread, avoiding SQLite's "check_same_thread" constraint.
_vanna_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="vanna")

class AgentState(TypedDict):
    query: str
    original_query: str          # keep the raw user input for fallback
    history: List[Dict[str, Any]]
    intent: str
    cot: Optional[str]
    sql: Optional[str]
    data: Optional[List[Dict[str, Any]]]
    chart: Optional[str]
    explanation: str
    success: bool
    error: Optional[str]

class ChatService:
    def __init__(self):
        self.provider = settings.DEFAULT_LLM_PROVIDER
        self.client = None

        logger.info(f"ChatService initializing with provider: {self.provider}")

        if self.provider == "gemini":
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel
                vertexai.init(project=settings.GOOGLE_CLOUD_PROJECT, location=settings.GOOGLE_CLOUD_LOCATION)
                self.client = GenerativeModel(settings.GEMINI_MODEL)
                logger.info(f"ChatService initialized with Gemini: {settings.GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI: {e}")
        elif settings.OPENROUTER_API_KEY:
            import openai
            self.client = openai.OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            logger.info("ChatService initialized with OpenRouter")
        elif settings.OPENAI_API_KEY:
            import openai
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("ChatService initialized with OpenAI")

        if not self.client:
            logger.warning(f"ChatService: No LLM client initialized! provider={self.provider}, OPENROUTER_API_KEY={'set' if settings.OPENROUTER_API_KEY else 'not set'}, OPENAI_API_KEY={'set' if settings.OPENAI_API_KEY else 'not set'}")
            
        self.workflow = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("determine_intent", self._intent_node)
        workflow.add_node("rephrase_query", self._rephrase_node)
        workflow.add_node("generate_cot", self._cot_node)
        workflow.add_node("execute_query", self._vanna_node)
        workflow.add_node("summarize_results", self._summarize_node)
        workflow.add_node("natural_chat", self._text_node)

        # Set Entry Point
        workflow.set_entry_point("determine_intent")

        # Add Conditional Edges
        workflow.add_conditional_edges(
            "determine_intent",
            self._route_intent,
            {
                "data": "rephrase_query",
                "text": "natural_chat"
            }
        )

        workflow.add_edge("rephrase_query", "generate_cot")
        workflow.add_edge("generate_cot", "execute_query")
        workflow.add_edge("execute_query", "summarize_results")
        workflow.add_edge("summarize_results", END)
        workflow.add_edge("natural_chat", END)

        return workflow.compile()

    # --- Nodes ---

    async def _intent_node(self, state: AgentState):
        """Determine if the query is a data query or text chat."""
        query = state["query"]
        history = state["history"]
        
        # Normalize history: ensure roles are assistant/user
        normalized_history = []
        for msg in history:
            role = "assistant" if msg.get("role") in ["bot", "assistant"] else "user"
            normalized_history.append({"role": role, "content": msg.get("content", "")})
        
        if not self.client:
            keywords = ["売上", "統計", "データ", "件数", "平均", "ランキング", "客", "注文", "在庫", "国", "地域", "推移", "上位", "グラフ"]
            intent = "data" if any(kw in query for kw in keywords) else "text"
            return {"intent": intent, "history": normalized_history}

        # Sticky intent: if we were doing data analysis and the query is short/vague
        last_intent = "text"
        if normalized_history:
            # Check if last bot message was data-heavy (has SQL or Chart) or if we can infer from content
            # For simplicity, if history exists and query is very short, lean towards data if it was working
            if len(query.strip()) < 10:
                # Clarifications like "Sales", "By region", "More numbers"
                return {"intent": "data", "history": normalized_history}

        messages = [
            {"role": "system", "content": "You are an intent classifier for a BI tool. Determine if the user message requires data analysis, SQL generation, or follow-up on a previous chart/data result. Also consider context. Respond with ONLY 'data' or 'text'."},
            *normalized_history[-5:],
            {"role": "user", "content": query}
        ]
        
        try:
            intent_raw = await self._call_llm(messages, max_tokens=10)
            intent = intent_raw.strip().lower()
            return {"intent": "data" if "data" in intent else "text", "history": normalized_history}
        except:
            return {"intent": "data", "history": normalized_history}

    async def _call_llm(self, messages: List[Dict[str, Any]], temperature: float = 0, max_tokens: int = 500) -> str:
        """Helper to call LLM based on provider."""
        if not self.client:
            raise ValueError(f"LLMクライアントが初期化されていません (provider={self.provider}). API keyまたはGCP認証情報を確認してください。")

        if self.provider == "gemini":
            from vertexai.generative_models import Content, Part
            
            # Convert messages to Vertex AI format
            contents = []
            system_instruction = None
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    system_instruction = content
                else:
                    v_role = "user" if role == "user" else "model"
                    contents.append(Content(role=v_role, parts=[Part.from_text(content)]))
            
            # Re-initialize model with system instruction if present
            if system_instruction:
                from vertexai.generative_models import GenerativeModel
                model = GenerativeModel(settings.GEMINI_MODEL, system_instruction=system_instruction)
            else:
                model = self.client
                
            response = await model.generate_content_async(
                contents,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            return response.text
        else:
            # OpenAI / OpenRouter
            model_name = settings.OPENROUTER_MODEL if settings.OPENROUTER_API_KEY else "gpt-4o"
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content

    async def _rephrase_node(self, state: AgentState):
        """Rephrase the user query into a standalone query based on context."""
        query = state["query"]
        history = state["history"] # Already normalized in intent_node
        
        if not history:
            return {"query": query}
            
        messages = [
            {"role": "system", "content": """You are a query rephraser for a BI tool. 
Task: Synthesize the user's latest input and the conversation history into a single, concrete, standalone question.
Rules:
1. Include all necessary metrics (e.g., Sales, Count) and dimensions (e.g., Region, Country) from the context.
2. NEVER use terms like "the previous analysis" or "the result above". Instead, repeat the actual metrics and dimensions (e.g., "Show the country-wise sales details").
3. If the user asks a pivot question (e.g., "By region instead"), rephrase to "Show sales by region".
4. If the user asks for details (e.g., "Show numbers"), rephrase to "Provide detailed data for [Actual Metric] by [Actual Dimension]".
5. The output must be a clear, standalone question in Japanese.
6. Provide ONLY the rephrased question."""},
            *history[-5:],
            {"role": "user", "content": f"Latest input: {query}"}
        ]
        
        try:
            rephrased_query = await self._call_llm(messages)
            rephrased_query = rephrased_query.strip()
            logger.info(f"Rephrased query: {query} -> {rephrased_query}")
            return {"query": rephrased_query}
        except:
            return {"query": query}

    def _route_intent(self, state: AgentState):
        return state["intent"]

    async def _cot_node(self, state: AgentState):
        """Generate Chain of Thought."""
        # Use the (potentially rephrased) query from state
        query = state["query"]
        history = state["history"]
        
        messages = [
            {"role": "system", "content": "あなたはデータ分析アシスタントです。質問に対して、どのようなデータをどのテーブルからどのように集計して調査するか、一言で方針を述べてください。回答は日本語で、「〜を調査します」のような形式にしてください。"},
            *history[-3:],
            {"role": "user", "content": query}
        ]
        
        try:
            cot_resp = await self._call_llm(messages, max_tokens=150)
            return {"cot": cot_resp.strip()}
        except:
            return {"cot": "データベースの状況を確認いたします。"}

    async def _run_in_vanna_thread(self, fn, *args):
        """Run a sync function in the dedicated Vanna thread to keep
        ChromaDB/SQLite happy (same-thread constraint)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_vanna_executor, fn, *args)

    async def _generate_sql_with_fallback(self, query: str, original_query: str) -> str:
        """Try generate_sql with the (rephrased) query, fall back to original."""
        try:
            sql = await self._run_in_vanna_thread(vanna_service.generate_sql, query)
            if sql:
                return sql
        except VannaNoSQLError:
            if query == original_query:
                raise
            logger.warning("_generate_sql_with_fallback: rephrased query got non-SQL, retrying original")

        # Fallback with original query
        if query != original_query:
            return await self._run_in_vanna_thread(vanna_service.generate_sql, original_query)

        return None

    _MAX_RESULT_ROWS = 500       # cap to avoid oversized responses
    _MAX_CHART_ROWS = 50          # Plotly works best with limited data

    async def _vanna_node(self, state: AgentState):
        """Execute Vanna SQL and Chart generation."""
        query = state["query"]
        original_query = state.get("original_query", query)

        try:
            sql = await self._generate_sql_with_fallback(query, original_query)

            if not sql:
                return {"success": False, "error": "SQLの生成に失敗しました。"}

            df = await self._run_in_vanna_thread(vanna_service.run_sql, sql)
            logger.info(f"_vanna_node: run_sql returned {len(df)} rows")

            # Cap rows to keep response size manageable
            truncated = len(df) > self._MAX_RESULT_ROWS
            df_limited = df.head(self._MAX_RESULT_ROWS)
            results = df_limited.to_dict(orient="records")

            # Generate Chart (use further limited data for charting)
            chart_json = None
            try:
                df_chart = df.head(self._MAX_CHART_ROWS)
                fig = await self._run_in_vanna_thread(
                    vanna_service.generate_plotly_figure, df_chart, query, sql
                )
                if fig:
                    import plotly.io as pio
                    chart_json = pio.to_json(fig)
            except Exception as chart_err:
                logger.warning(f"_vanna_node: chart generation failed (non-fatal): {chart_err}")
                # Continue without chart — data is still valuable

            return {
                "sql": sql,
                "data": results,
                "chart": chart_json,
                "success": True
            }
        except VannaNoSQLError as e:
            # LLM explained why it can't generate SQL — show that to the user
            explanation = str(e)
            logger.info(f"_vanna_node: LLM declined SQL generation: {explanation[:120]}")
            return {"success": True, "explanation": explanation}
        except Exception as e:
            logger.error(f"_vanna_node error: {e}")
            return {"success": False, "error": str(e)}

    async def _summarize_node(self, state: AgentState):
        """Summarize results."""
        if not state.get("success"):
            return {"explanation": f"エラーが発生しました: {state.get('error')}"}
            
        query = state["query"]
        data = state.get("data", [])
        cot = state.get("cot", "")
        
        data_str = str(data)[:2000]
        messages = [
            {"role": "system", "content": "あなたは優秀なデータアナリストです。取得したデータに基づき、ユーザーの質問に対する回答を簡潔かつ丁寧に日本語で作成してください。主要なポイントを伝えてください。"},
            {"role": "user", "content": f"質問: {query}\n調査方針: {cot}\n分析データ: {data_str}\n\n回答を作成してください:"}
        ]
        
        try:
            summary = await self._call_llm(messages, temperature=0.3)
            summary = summary.strip()
            return {"explanation": f"{cot}\n\n---\n\n{summary}"}
        except:
            return {"explanation": f"{cot}\n\n---\nデータの抽出が完了しました。"}

    async def _text_node(self, state: AgentState):
        """Standard chat response."""
        query = state["query"]
        history = state["history"]
        
        messages = [
            {"role": "system", "content": "You are Tabi, a helpful BI assistant. Respond politely in Japanese."},
            *history[-5:],
            {"role": "user", "content": query}
        ]
        
        try:
            resp_text = await self._call_llm(messages, temperature=0.7)
            return {"explanation": resp_text.strip(), "success": True}
        except Exception as e:
            return {"explanation": f"エラーが発生しました: {str(e)}", "success": False}

    # --- Public API ---

    @staticmethod
    def _trim_history(conversation_history: List[Dict[str, Any]], max_entries: int = 10, max_content_len: int = 500) -> List[Dict[str, Any]]:
        """Keep only recent history entries with truncated content."""
        recent = conversation_history[-max_entries:] if len(conversation_history) > max_entries else conversation_history
        trimmed = []
        for msg in recent:
            content = msg.get("content", "")
            if len(content) > max_content_len:
                content = content[:max_content_len] + "…"
            trimmed.append({"role": msg.get("role", "user"), "content": content})
        return trimmed

    async def process_chat(self, query: str, conversation_history: List[Dict[str, Any]] = []) -> Dict[str, Any]:
        """Process chat using LangGraph workflow."""
        trimmed_history = self._trim_history(conversation_history)
        initial_state = {
            "query": query,
            "original_query": query,
            "history": trimmed_history,
            "intent": "text",
            "cot": None,
            "sql": None,
            "data": None,
            "chart": None,
            "explanation": "",
            "success": False,
            "error": None
        }
        
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            return {
                "success": final_state.get("success", False),
                "type": "data" if final_state["intent"] == "data" else "text",
                "sql": final_state.get("sql"),
                "data": final_state.get("data"),
                "chart": final_state.get("chart"),
                "explanation": final_state.get("explanation", "エラーが発生しました。"),
                "error": final_state.get("error")
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"LangGraph execution error: {e}\n{error_details}")
            return {"success": False, "error": f"処理中にエラーが発生しました: {str(e) or type(e).__name__}"}

chat_service = ChatService()
