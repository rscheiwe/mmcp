def format_tool_name(name: str) -> str:
    """Format tool name to follow Python PascalCase naming conventions."""
    formatted = name.replace(' ', '_').replace('-', '_')
    formatted = ''.join(word.capitalize() for word in formatted.split('_'))
    formatted = ''.join(c for c in formatted if c.isalnum())
    if formatted and not formatted[0].isalpha():
        formatted = 'Tool' + formatted
    return formatted
