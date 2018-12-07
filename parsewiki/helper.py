
def create_context(edit, text, length = 500, seperator = ['<b>', '</b>'], overlap = 90):
    """
    Wrap context around an edit made by a user. 
    
    Use this method to extract the preceding and following defined number of characters from the main 
    text. This method uses utf8 encoding, because otherwise Arabic, Hebrew, or Chinese texts won't be 
    handled properly.

    Args:
        edit: The actual edit made by the user
        text: The entire Wikipedia text in which the edit was made
        length: The number of characters that is required to create context (default: 500)
        seperator: A character to mark the beginning and end of the edit (default: ['<b>', '</b>'])
        overlap: The level of text overlap required in case a 100% match is not found (default: 90)
        
    Returns:
        A string with the context or None if there is no match.

    """

    edit = edit.encode('utf8')
    text = text.encode('utf8')
    
    split = text.rpartition(edit)
        
    # If there is no exact match between the edit and the text, try to find a closest match as possible
    if not split[1]:
        
        prefix = suffix = None
        
        edit_length = len(edit)

        for i in range(100, (100 - overlap), -1):            
            charlen = round(edit_length * ((i - 1) / 100))
            index = text.find(edit[:charlen])
            
            if charlen is 0:
                break

            # We have a match
            if index is not -1:
                split = text.rpartition(edit[:charlen])                
                prefix = split[0].decode('utf8')[-length:]
                break
        
        for i in range(0, overlap, 1):            
            charlen = round(edit_length * ((i + 1) / 100))
            index = text.find(edit[charlen:])
            
            if charlen is 0:
                break
            
            # We have a match
            if index is not -1:
                split = text.rpartition(edit[charlen:])                
                suffix = split[2].decode('utf8')[:length]
                break
        
        middle = edit.decode('utf8')
        
        if not prefix or not suffix:
            return None
    
    # We have a 100% match
    else:
        
        prefix = split[0].decode('utf8')[-length:]
        middle = split[1].decode('utf8')
        suffix = split[2].decode('utf8')[:length]
    
    
    # Remove the first and last word from the predefined character length of context
    prefix = ' '.join(prefix.split(' ')[1:])
    suffix = ' '.join(suffix.split(' ')[:-1]) 
    
    # Add an ellipsis before and after the context if there is any context available
    if len(prefix) is not 0:
        prefix = ''.join(['...', prefix])
    if len(suffix) is not 0:
        suffix = ''.join([suffix, '...'])
    
    context = ''.join([prefix, ''.join([seperator[0], middle, seperator[1]]), suffix])

    return context
