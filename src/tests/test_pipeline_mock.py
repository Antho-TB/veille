# ---------------------------------------------------------------------------
# Tests Unitaires - Pipeline de Veille
# ---------------------------------------------------------------------------
# Ce script de test permet de :
# 1. Valider la logique du pipeline sans appeler les vraies API (Mock).
# 2. Tester l'extraction JSON et le formatage des données.
# 3. Assurer la stabilité du code avant déploiement.
# ---------------------------------------------------------------------------

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())
from src.core.pipeline import DataManager, VectorEngine, Config
from src.core.brain_new import Brain

class TestPipelineMock(unittest.TestCase):

    @patch('src.core.pipeline.gspread')
    @patch('src.core.pipeline.ServiceAccountCredentials')
    def test_data_manager_load_data(self, mock_creds, mock_gspread):
        print("\n--- Test DataManager.load_data (Mock) ---")
        # Setup mock
        mock_client = MagicMock()
        mock_gspread.authorize.return_value = mock_client
        mock_sheet = MagicMock()
        mock_client.open_by_key.return_value = mock_sheet
        
        # Mock worksheet data - matching actual column names from Google Sheets
        mock_worksheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_worksheet
        # We need side_effect to return data for Base_Active, then empty for others
        mock_worksheet.get_all_records.side_effect = [
            [{"Intitulé ": "Test Document", "Lien Internet": "http://test.com", "Statut": "A traiter", "Commentaires": "Rien"}],
            [],
            [],
            [{'keywords': 'test'}] # for Config_IA
        ]

        # Execute
        dm = DataManager()
        
        # Mock os.path.exists to avoid needing real credentials.json
        with patch('os.path.exists', return_value=True):
             df, conf = dm.load_data()

        # Verify
        self.assertFalse(df.empty)
        self.assertIn('titre', df.columns)
        self.assertEqual(df.iloc[0]['titre'], "Test Document")
        self.assertEqual(df.iloc[0]['url'], "http://test.com")
        print("✅ DataManager loaded data correctly (mocked).")

    @patch('src.core.pipeline.chromadb.Client')
    def test_vector_engine_index(self, mock_chroma_client):
        print("\n--- Test VectorEngine.index (Mock) ---")
        # Setup
        mock_collection = MagicMock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection
        # Mock count to be 0 so it indexes
        mock_collection.count.return_value = 0
        
        ve = VectorEngine()
        df = pd.DataFrame({'titre': ['Doc 1', 'Doc 2']})
        
        # Execute
        ve.index(df)
        
        # Verify
        mock_collection.upsert.assert_called()
        self.assertEqual(mock_collection.upsert.call_count, 1)
        print("✅ VectorEngine indexed documents (mocked).")

    @patch('src.core.brain_new.genai.GenerativeModel')
    def test_brain_audit(self, mock_model_class):
        print("\n--- Test Brain.audit_manquants (Mock) ---")
        # Setup
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        # Mock JSON response from Gemini
        mock_response.text = '```json\n[{"titre": "Manquant 1", "criticite": "Haute", "resume": "...", "action": "Ajouter"}]\n```'
        mock_model.generate_content.return_value = mock_response
        
        brain = Brain()
        current_list = ["Doc A", "Doc B"]
        
        # Execute
        result = brain.audit_manquants(current_list)
        
        # Verify
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['titre'], "Manquant 1")
        print("✅ Brain audit returned parsed JSON (mocked).")

    @patch('src.core.brain_new.requests.get')
    def test_brain_search(self, mock_get):
        print("\n--- Test Brain.search (Mock) ---")
        # Setup
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'items': [{'title': 'News 1', 'snippet': 'Desc 1', 'link': 'http://news1.com'}]
        }
        mock_get.return_value = mock_response
        
        brain = Brain()
        
        # Execute
        results = brain.search("query", search_api_key="mock_key", search_engine_id="mock_cx")
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['titre'], "News 1")
        print("✅ Brain search returned results (mocked).")

if __name__ == '__main__':
    unittest.main()
