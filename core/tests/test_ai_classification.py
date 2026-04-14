from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from core.utils.ai_handler import AIHandler
from core.models import Department, Grievance, User

class AIClassificationTest(APITestCase):
    def setUp(self):
        # Create some departments
        self.roads = Department.objects.create(name="Roads", description="Roads and Transport")
        self.water = Department.objects.create(name="Water", description="Water Supply")
        self.user = User.objects.create_user(username='testcitizen', password='password', role='citizen')

    @patch('core.utils.ai_handler.ChatGroq')
    def test_ai_handler_parsing(self, MockChatGroq):
        # Setup mock behavior
        mock_llm = MockChatGroq.return_value
        
        ai = AIHandler()
        
        raw_output = """
        Department: Roads
        Urgency: High
        Summary: Pothole issue
        """
        parsed = ai._parse_result(raw_output)
        self.assertEqual(parsed['department'], 'Roads')
        self.assertEqual(parsed['urgency'], 'high')

    @patch('core.utils.ai_handler.ChatGroq')
    def test_ai_handler_translation(self, MockChatGroq):
        # Setup mock behavior
        mock_llm = MockChatGroq.return_value
        # Mocking RunnableSequence.invoke is tricky, better mock the chain result if possible
        # but here we are mocking ChatGroq itself.
        
        # Actually, for testing translate_to_english, we need to mock the response of the chain.
        # It's better to patch the invoke method of the chain objects if possible, 
        # or just mock the final output parser result.
        
        ai = AIHandler()
        
        with patch('langchain_core.runnables.RunnableSequence.invoke') as mock_invoke:
            mock_invoke.return_value = "Water problem"
            
            translated = ai.translate_to_english("தண்ணீர் பிரச்சனை")
            self.assertEqual(translated, "Water problem")
            mock_invoke.assert_called_once()

    def test_view_integration(self):
        # This tests that the view uses the department name correctly
        # We will mock AIHandler.analyze_grievance to return a specific department
        
        with patch('core.utils.ai_handler.AIHandler.analyze_grievance') as mock_analyze:
            mock_analyze.return_value = {
                'department': 'Water',
                'urgency': 'critical',
                'summary': 'Water leak detected'
            }
            
            self.client.force_authenticate(user=self.user)
            
            data = {
                'title': 'Leaking pipe',
                'description': 'Water is leaking everywhere'
            }
            
            response = self.client.post('/api/grievances/', data)
            if response.status_code != 201:
                print(f"DEBUG: Status: {response.status_code}")
                try:
                    print(f"DEBUG: Data: {response.data}")
                except:
                    print(f"DEBUG: Content: {response.content}")
            self.assertEqual(response.status_code, 201)
            
            grievance = Grievance.objects.get(title='Leaking pipe')
            self.assertEqual(grievance.department, self.water)
            self.assertEqual(grievance.urgency, 'critical')
