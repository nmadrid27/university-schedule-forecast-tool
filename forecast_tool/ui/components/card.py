"""
shadcn/ui Card Component
Generates HTML for cards with shadcn styling
"""

def card(
    title: str = None,
    description: str = None,
    content: str = "",
    footer: str = None,
    class_name: str = ""
) -> str:
    """
    Generate shadcn-styled card HTML

    Args:
        title: Card title (h3)
        description: Card description/subtitle (p)
        content: Main card content (HTML string)
        footer: Footer content (HTML string)
        class_name: Additional CSS classes

    Returns:
        HTML string for card
    """
    # Header (title + description)
    header_html = ""
    if title or description:
        title_html = f'<h3 class="text-2xl font-semibold leading-none tracking-tight">{title}</h3>' if title else ''
        desc_html = f'<p class="text-sm text-muted-foreground">{description}</p>' if description else ''
        header_html = f'''
        <div class="flex flex-col space-y-1.5 p-6">
            {title_html}
            {desc_html}
        </div>
        '''

    # Footer
    footer_html = f'<div class="flex items-center p-6 pt-0">{footer}</div>' if footer else ''

    # Card container
    return f'''
    <div class="rounded-lg border bg-card text-card-foreground shadow-sm {class_name}">
        {header_html}
        <div class="p-6 {'pt-0' if header_html else ''}">
            {content}
        </div>
        {footer_html}
    </div>
    '''
