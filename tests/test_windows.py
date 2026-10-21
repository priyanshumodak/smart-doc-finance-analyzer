import unittest
from backend.token_windows import word_windows

class Encoding:
    def __init__(self,ids):
        self.ids=ids
    def word_ids(self):
        return self.ids

class Tokenizer:
    def __call__(self,words,**kwargs):
        return Encoding([index for index,word in enumerate(words) for _ in word])
    def num_special_tokens_to_add(self,pair=False):
        return 2

class WindowTests(unittest.TestCase):
    def test_every_word_preserved_without_breaking_short_entity(self):
        words=['a']*12
        labels=['O']*8+['B-VENDOR_NAME','I-VENDOR_NAME','I-VENDOR_NAME','O']
        windows=word_windows(words,[[0,0,1,1]]*12,Tokenizer(),12,labels)
        self.assertEqual([i for start,end in windows for i in range(start,end)],list(range(12)))
        self.assertTrue(all(not labels[start].startswith('I-') for start,end in windows))
        self.assertTrue(all(end-start+2<=12 for start,end in windows))
    def test_unrepresentable_single_word_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError,'single OCR word'):
            word_windows(['a'*20],[[0,0,1,1]],Tokenizer(),12)

if __name__=='__main__':
    unittest.main()
