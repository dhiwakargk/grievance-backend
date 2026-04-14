import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from django.conf import settings
import base64

class AIHandler:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        # Fallback or error if key missing, but for now allow init
        if not api_key:
            print("WARNING: GROQ_API_KEY not found in env.")
            self.llm = None
        else:
            self.llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name="llama-3.3-70b-versatile")

    def translate_to_english(self, text):
        if not self.llm or not text:
            return text

        prompt_template = """
        You are a translator. If the following text is in English, return it exactly as it is.
        If it is in any other language (especially Tamil), translate it to English.
        Return ONLY the translated English text. No explanations.

        Text: {text}
        """
        
        prompt = PromptTemplate(template=prompt_template, input_variables=["text"])
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            translated = chain.invoke({"text": text}).strip()
            print(f"DEBUG: LLM Translate Response for '{text}': '{translated}'")
            # Handle cases where LLM returns common "empty" indicators
            if translated.lower().replace('.', '') in ["nil", "none", "empty", "null"]:
                return text
            return translated
        except Exception as e:
            print(f"Translation Error: {e}")
            return text

    def analyze_grievance(self, text, valid_departments=None):
        if not self.llm:
            return {
                "department": "Unassigned",
                "urgency": "low",
                "summary": "AI Service Unavailable"
            }

        if valid_departments:
            dept_str = ", ".join(valid_departments)
        else:
            dept_str = "Roads, Water, Electricity, Police, Health, Sanitation"

        prompt_template = f"""
        You are an AI assistant for a government grievance system.
        Analyze the following grievance data and provide:
        1. The most suitable government department from this list ONLY: [{dept_str}]. If none match perfectly, choose the closest or "General".
        2. The urgency level (low, medium, high, critical). 
        3. A short summary (1-2 sentences).
        4. A very short, descriptive title (max 5 words).

        NOTE: Prioritize the "Extracted from Image" text if the Title or Description is vague or empty.
        Water scarcity, theft, and sanitation issues are ALWAYS "high" priority.

        {{text}}

        Format the output EXACTLY as:
        Suggested Title: <short_title>
        Department: <dept>
        Urgency: <urgency>
        Summary: <summary>
        """

        prompt = PromptTemplate(template=prompt_template, input_variables=["text"])
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            result = chain.invoke({"text": text})
            parsed_result = self._parse_result(result)
            
            # Enforce high priority for specific keywords override
            lower_text = text.lower()
            critical_keywords = ["theft", "water", "sanitation"]
            if any(k in lower_text for k in critical_keywords):
                # Only upgrade to high if it's not already critical
                if parsed_result.get("urgency") != "critical":
                     parsed_result["urgency"] = "high"
            
            return parsed_result
        except Exception as e:
            print(f"AI Error: {e}")
            return {
                "department": "Unassigned",
                "urgency": "medium",
                "summary": "Analysis failed"
            }

    def _parse_result(self, result_text):
        lines = result_text.strip().split('\n')
        data = {"department": "General", "urgency": "medium", "summary": "", "suggested_title": ""}
        for line in lines:
            line = line.strip()
            if line.startswith("Department:"):
                dept = line.replace("Department:", "").strip()
                # Clean up any extra punctuation or casing
                data["department"] = dept.split(' ')[0] if dept else "General" 
                # Ideally we want the full word, but sometimes they add extra text. 
                # Let's trust the clean output or just take the whole string and clean it in view.
                data["department"] = dept
            elif line.startswith("Urgency:"):
                data["urgency"] = line.replace("Urgency:", "").strip().lower()
            elif line.startswith("Summary:"):
                data["summary"] = line.replace("Summary:", "").strip()
            elif line.startswith("Suggested Title:"):
                data["suggested_title"] = line.replace("Suggested Title:", "").strip().strip('"').strip("'")
        return data

    def extract_text_from_image(self, image_file):
        """
        Uses Groq's Vision model to extract text from an image.
        """
        if not self.llm:
            return ""

        try:
            # Read and encode image to base64
            image_file.seek(0)
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # We need a vision model for this. 
            # Llama 3.2 11b/90b vision models are good options on Groq.
            vision_llm = ChatGroq(
                temperature=0, 
                groq_api_key=os.getenv("GROQ_API_KEY"), 
                model_name="meta-llama/llama-4-scout-17b-16e-instruct"
            )

            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Extract all readable text from this image. Return ONLY the extracted text. If no text is found, return an empty string."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ]
            )

            response = vision_llm.invoke([message])
            text_extracted = response.content.strip()
            print(f"DEBUG: Vision OCR Raw Response: '{text_extracted}'")
            return text_extracted

        except Exception as e:
            print(f"Vision OCR Error: {e}")
            return ""
