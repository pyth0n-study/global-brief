import unittest
from grounded_focus import validate_focus


class GroundedFocusTests(unittest.TestCase):
    def test_complete_original_sentence(self):
        sentence = '当局は計画を検討中で、まだ実施は決まっていません。'
        self.assertIsNotNone(validate_focus(sentence, sentence, '', sentence))

    def test_invented_or_truncated_or_missing_evidence_hidden(self):
        sentence = '当局は計画を検討中で、まだ実施は決まっていません。'
        for point, quote in [('計画の実施が決まりました。', sentence),
                             ('当局は計画を検討中', '当局は計画を検討中'),
                             (sentence, ''), ('', ''), (sentence, sentence)]:
            text = '' if (point, quote) == (sentence, sentence) else sentence
            self.assertIsNone(validate_focus(point, quote, '', text))
