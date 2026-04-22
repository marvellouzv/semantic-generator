import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class LLMConnector:
    def __init__(self, openai_api_key: str):
        self.client = AsyncOpenAI(api_key=openai_api_key)

    async def ask_openai(self, query: str, model: str = "gpt-4", temperature: float = 0.7, max_tokens: int = 500) -> str:
        try:
            # GPT-5 models use Responses API and don't support temperature
            if model.startswith("gpt-5"):
                logger.info(f"Using Responses API for {model} (no temperature)")
                response = await self.client.responses.create(
                    model=model,
                    input=[{
                        "role": "user",
                        "content": [{"type": "input_text", "text": query}]
                    }],
                    max_output_tokens=max_tokens
                )
                # Extract text from GPT-5 response
                # Response structure: output = [reasoning_item, message_item]
                # message_item.content[0].text contains the final answer
                if response.output:
                    for item in response.output:
                        # Look for message items (type='message')
                        item_dict = item if isinstance(item, dict) else (item.model_dump() if hasattr(item, 'model_dump') else {})
                        item_type = item_dict.get('type')
                        
                        if item_type == 'message':
                            content = item_dict.get('content', [])
                            if content and len(content) > 0:
                                # content[0] should have 'text' field
                                text_block = content[0]
                                if isinstance(text_block, dict) and 'text' in text_block:
                                    return text_block['text']
                
                # Fallback to output_text if available
                if response.output_text:
                    return response.output_text
                
                # If still nothing, log error
                logger.error(f"Could not extract text from GPT-5 response! Status: {response.status}")
                return f"[ERROR] Response status: {response.status}, no text extracted"
            else:
                # GPT-4/3.5 use Chat Completions API
                response = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": query}
                    ],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to query OpenAI: {str(e)}")
            raise