"""
String utility functions for safe string formatting.
Prevents f-string evaluation errors when content contains curly braces.
"""


def escape_for_fstring(text: str) -> str:
    """
    Escape curly braces in a string to prevent f-string evaluation errors.
    
    When using f-strings, Python evaluates anything in {} as a Python expression.
    If user data or document content contains {current_date} or similar patterns,
    Python will try to evaluate them as variables, causing NameError.
    
    This function escapes curly braces by doubling them: { becomes {{ and } becomes }}
    
    Args:
        text: String that may contain curly braces
        
    Returns:
        String with curly braces escaped (doubled)
        
    Example:
        >>> escape_for_fstring("Update: Current date is {current_date}")
        'Update: Current date is {{current_date}}'
    """
    if not isinstance(text, str):
        text = str(text)
    return text.replace('{', '{{').replace('}', '}}')

