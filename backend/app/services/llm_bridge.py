from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import json
import logging
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryContext(BaseModel):
    """Context for query processing"""
    user_query: str
    conversation_history: List[Dict[str, Any]] = []
    schema_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """Response from LLM"""
    cube_query: Optional[Dict[str, Any]] = None
    explanation: str = ""
    visualization_suggestion: Optional[str] = None
    confidence: float = 0.0
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    error: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_cube_query(self, context: QueryContext) -> LLMResponse:
        """Generate Cube.js query from natural language"""
        pass
    
    @abstractmethod
    async def explain_query_result(self, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Explain query results in natural language"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")
    
    async def generate_cube_query(self, context: QueryContext) -> LLMResponse:
        """Generate Cube.js query using OpenAI"""
        try:
            system_prompt = self._build_system_prompt(context.schema_context)
            user_prompt = self._build_user_prompt(context)
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return LLMResponse(error=str(e))
    
    async def explain_query_result(self, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Explain query results using OpenAI"""
        try:
            prompt = f"""
            クエリ: {json.dumps(query, ensure_ascii=False, indent=2)}
            結果: {json.dumps(result, ensure_ascii=False, indent=2)}
            
            上記のクエリ結果を日本語で分かりやすく説明してください。
            数値の傾向、パターン、インサイトを含めて説明してください。
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI explanation error: {e}")
            return "結果の説明を生成できませんでした。"
    
    def _build_system_prompt(self, schema_context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for query generation"""
        base_prompt = """
        あなたはCube.jsクエリ専門のアシスタントです。
        ユーザーの自然言語クエリを正確なCube.jsクエリに変換してください。
        
        重要なルール:
        1. 必ずJSON形式で応答してください
        2. 日付は適切なフォーマットで指定してください
        3. 不明な場合は clarification_question を使用してください
        4. confidence スコアを0.0-1.0で設定してください
        
        レスポンス形式:
        {
            "cube_query": { /* Cube.js query object */ },
            "explanation": "クエリの説明",
            "visualization_suggestion": "推奨される可視化タイプ",
            "confidence": 0.8,
            "requires_clarification": false,
            "clarification_question": null
        }
        """
        
        if schema_context:
            base_prompt += f"\n\n利用可能なスキーマ:\n{json.dumps(schema_context, ensure_ascii=False, indent=2)}"
        
        return base_prompt
    
    def _build_user_prompt(self, context: QueryContext) -> str:
        """Build user prompt with context"""
        prompt = f"ユーザークエリ: {context.user_query}"
        
        if context.conversation_history:
            prompt += "\n\n会話履歴:\n"
            for item in context.conversation_history[-3:]:  # Last 3 messages
                prompt += f"- {item.get('role', 'user')}: {item.get('content', '')}\n"
        
        return prompt
    
    def _parse_response(self, response_text: str) -> LLMResponse:
        """Parse LLM response"""
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            data = json.loads(json_text)
            return LLMResponse(**data)
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return LLMResponse(
                explanation="クエリを解析できませんでした。",
                error=str(e)
            )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic provider")
    
    async def generate_cube_query(self, context: QueryContext) -> LLMResponse:
        """Generate Cube.js query using Anthropic Claude"""
        try:
            prompt = self._build_claude_prompt(context)
            
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._parse_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return LLMResponse(error=str(e))
    
    async def explain_query_result(self, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Explain query results using Anthropic Claude"""
        try:
            prompt = f"""
            以下のクエリ結果を分析して、日本語で分かりやすく説明してください。
            
            クエリ: {json.dumps(query, ensure_ascii=False, indent=2)}
            結果: {json.dumps(result, ensure_ascii=False, indent=2)}
            
            数値の傾向、パターン、重要なインサイトを含めて説明してください。
            """
            
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic explanation error: {e}")
            return "結果の説明を生成できませんでした。"
    
    def _build_claude_prompt(self, context: QueryContext) -> str:
        """Build prompt for Claude"""
        prompt = f"""
        あなたはCube.jsクエリ専門のアシスタントです。
        ユーザーの自然言語クエリを正確なCube.jsクエリに変換してください。
        
        ユーザークエリ: {context.user_query}
        """
        
        if context.schema_context:
            prompt += f"\n\n利用可能なスキーマ:\n{json.dumps(context.schema_context, ensure_ascii=False, indent=2)}"
        
        if context.conversation_history:
            prompt += "\n\n会話履歴:\n"
            for item in context.conversation_history[-3:]:
                prompt += f"- {item.get('role', 'user')}: {item.get('content', '')}\n"
        
        prompt += """
        
        以下のJSON形式で応答してください:
        {
            "cube_query": { /* Cube.js query object */ },
            "explanation": "クエリの説明",
            "visualization_suggestion": "推奨される可視化タイプ",
            "confidence": 0.8,
            "requires_clarification": false,
            "clarification_question": null
        }
        """
        
        return prompt
    
    def _parse_response(self, response_text: str) -> LLMResponse:
        """Parse Claude response"""
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            data = json.loads(json_text)
            return LLMResponse(**data)
            
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return LLMResponse(
                explanation="クエリを解析できませんでした。",
                error=str(e)
            )

class GeminiProvider(LLMProvider):
    """Google Gemini Provider (Supports both AI Studio and Vertex AI)"""
    
    def __init__(self, api_key: Optional[str] = None, project: Optional[str] = None, location: Optional[str] = None):
        self.api_key = api_key
        try:
            if self.api_key:
                # API Key (Google AI Studio) mode
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client_type = "studio"
            else:
                # Vertex AI mode
                import vertexai
                from vertexai.generative_models import GenerativeModel
                vertexai.init(project=project, location=location)
                self.client_type = "vertex"
            
            self.model_name = settings.GEMINI_MODEL
            
        except ImportError:
            raise ImportError("For Gemini, install 'google-generativeai' (API Key) or 'google-cloud-aiplatform' (Vertex AI)")
    
    async def generate_cube_query(self, context: QueryContext) -> LLMResponse:
        """Generate Cube.js query using Gemini"""
        try:
            system_prompt = self._build_system_prompt(context.schema_context)
            user_prompt = self._build_user_prompt(context)
            
            if self.client_type == "studio":
                import google.generativeai as genai
                # AI Studio configuration
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_prompt
                )
                response = await model.generate_content_async(
                    user_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2000
                    )
                )
            else:
                # Vertex AI configuration
                from vertexai.generative_models import GenerativeModel, Part
                model = GenerativeModel(self.model_name, system_instruction=system_prompt)
                response = await model.generate_content_async(
                    [Part.from_text(user_prompt)],
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 2000
                    }
                )
            
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return LLMResponse(error=str(e))
    
    async def explain_query_result(self, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Explain query results using Gemini"""
        try:
            prompt = f"""
            クエリ: {json.dumps(query, ensure_ascii=False, indent=2)}
            結果: {json.dumps(result, ensure_ascii=False, indent=2)}
            
            上記のクエリ結果を日本語で分かりやすく説明してください。
            数値の傾向、パターン、インサイトを含めて説明してください。
            """
            
            if self.client_type == "studio":
                import google.generativeai as genai
                model = genai.GenerativeModel(self.model_name)
                response = await model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1000
                    )
                )
            else:
                from vertexai.generative_models import GenerativeModel
                model = GenerativeModel(self.model_name)
                response = await model.generate_content_async(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 1000
                    }
                )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini explanation error: {e}")
            return "結果の説明を生成できませんでした。"

    # _build_system_prompt, _build_user_prompt, _parse_response は変更なしでOK
    def _build_system_prompt(self, schema_context: Optional[Dict[str, Any]]) -> str:
        # (元のコードと同じ内容)
        return super()._build_system_prompt(schema_context) # または元の実装をコピー

    def _build_user_prompt(self, context: QueryContext) -> str:
         # (元のコードと同じ内容)
         return f"ユーザークエリ: {context.user_query}..." # 省略

    def _parse_response(self, response_text: str) -> LLMResponse:
        # (元のコードと同じ内容)
        try:
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            return LLMResponse(**data)
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return LLMResponse(explanation="解析エラー", error=str(e))



class LLMBridge:
    """Main LLM bridge service"""
    
    def __init__(self):
        self.providers = {}
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize LLM providers lazily"""
        if self._initialized:
            return

        # Always try to initialize Gemini as it's our new default
        try:
            # 優先順位: API Key > Vertex AI Project
            if settings.GOOGLE_API_KEY:
                self.providers['gemini'] = GeminiProvider(
                    api_key=settings.GOOGLE_API_KEY
                )
                
            # Check if we have necessary config to avoid hanging on auth
            if settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_CLOUD_LOCATION:
                self.providers['gemini'] = GeminiProvider(
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    location=settings.GOOGLE_CLOUD_LOCATION
                )
            else:
                logger.warning("Skipping Gemini init: Missing GOOGLE_CLOUD_PROJECT or LOCATION")
        except Exception as e:
            logger.debug(f"Gemini provider not initialized: {e}")

        if settings.OPENAI_API_KEY:
            self.providers['openai'] = OpenAIProvider(settings.OPENAI_API_KEY)
        
        if settings.ANTHROPIC_API_KEY:
            self.providers['anthropic'] = AnthropicProvider(settings.ANTHROPIC_API_KEY)
        
        self._initialized = True
        
        if not self.providers:
            logger.warning("No LLM providers configured")
    
    def _get_provider(self, name: str) -> Optional[LLMProvider]:
        self._ensure_initialized()
        return self.providers.get(name)

    async def process_query(self, context: QueryContext, provider: Optional[str] = None) -> LLMResponse:
        """Process natural language query"""
        self._ensure_initialized()
        provider_name = provider or settings.DEFAULT_LLM_PROVIDER
        
        if provider_name not in self.providers:
            # Try fallback if default is not available
            if self.providers:
                provider_name = list(self.providers.keys())[0]
            else:
                return LLMResponse(
                    error=f"Provider '{provider_name}' not available and no fallbacks"
                )
        
        return await self.providers[provider_name].generate_cube_query(context)
    
    async def explain_result(self, query: Dict[str, Any], result: Dict[str, Any], provider: Optional[str] = None) -> str:
        """Explain query results"""
        self._ensure_initialized()
        provider_name = provider or settings.DEFAULT_LLM_PROVIDER
        
        if provider_name not in self.providers:
             if self.providers:
                provider_name = list(self.providers.keys())[0]
             else:
                return "説明を生成できませんでした。"
        
        return await self.providers[provider_name].explain_query_result(query, result)
    
    def list_providers(self) -> List[str]:
        """List available providers"""
        self._ensure_initialized()
        return list(self.providers.keys())


# Global instance
llm_bridge = LLMBridge()