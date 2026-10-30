import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch


class SocialTests(unittest.TestCase):
    def test_public_reactions_comments_and_validation(self):
        import app as module
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder, patch.object(module, 'DATABASE', str(Path(folder) / 'social.db')), patch.object(module, '_social_posts', {}):
            module.init_db()
            client = module.app.test_client()
            article = 'a' * 32
            response = client.post('/api/react', json=dict(url_hash=article, reaction='heart', action='add'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['count'], 1)
            self.assertEqual(client.post('/api/reactions', json={'hashes': [article]}).json[article]['heart'], 1)
            self.assertEqual(client.post('/api/comment', json=dict(url_hash=article, nickname='テスト', body='<script>本文</script>')).status_code, 200)
            self.assertEqual(client.get('/api/comments/' + article).json[0]['body'], '<script>本文</script>')
            self.assertEqual(client.post('/api/comment', json=dict(url_hash=article, nickname='a', body='x' * 501)).status_code, 400)
            self.assertEqual(client.post('/api/react', json=dict(url_hash=article, reaction=[], action='add')).status_code, 400)
            self.assertEqual(client.post('/api/react', json=dict(url_hash=article, reaction='heart', action='add'), headers={'Origin': 'https://other.example'}).status_code, 403)
            self.assertEqual(client.post('/api/reactions', json={'hashes': [article] * 51}).status_code, 400)
