"""Word-aligned model windows sized by actual subword counts, without silent truncation."""
def word_windows(words,boxes,tokenizer,max_length=512,labels=None):
    if not words:
        return []
    encoded=tokenizer(words,boxes=boxes,add_special_tokens=False,truncation=False)
    counts=[0]*len(words)
    for word_id in encoded.word_ids():
        if word_id is not None:
            counts[word_id]+=1
    budget=max_length-tokenizer.num_special_tokens_to_add(pair=False)
    windows=[]
    start=0
    while start<len(words):
        end=start
        used=0
        while end<len(words) and used+counts[end]<=budget:
            used+=counts[end]
            end+=1
        if end==start:
            raise ValueError('A single OCR word exceeds the model token budget')
        if labels and end<len(words) and labels[end].startswith('I-'):
            boundary=end
            while boundary>start and labels[boundary].startswith('I-'):
                boundary-=1
            if boundary>start:
                end=boundary
        windows.append((start,end))
        start=end
    return windows
