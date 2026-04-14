from .ai_handler import AIHandler

class OCRHandler:
    @staticmethod
    def extract_text(image_file):
        try:
            ai = AIHandler()
            text = ai.extract_text_from_image(image_file)
            return text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
