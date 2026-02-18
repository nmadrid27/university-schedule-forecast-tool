"""
shadcn/ui Alert Component
Generates HTML for alerts/notifications with shadcn styling
"""

def alert(
    title: str,
    description: str = None,
    variant: str = "default",
    icon: str = None
) -> str:
    """
    Generate shadcn-styled alert HTML

    Args:
        title: Alert title
        description: Alert description (optional)
        variant: 'default' | 'destructive'
        icon: Lucide icon name

    Returns:
        HTML string for alert
    """
    # Variant classes
    variant_classes = {
        'default': 'bg-background text-foreground',
        'destructive': 'border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive'
    }

    # Icon HTML
    icon_html = ""
    if icon:
        icon_html = f'<i data-lucide="{icon}" class="h-4 w-4"></i>'

    # Description
    desc_html = f'<div class="text-sm [&_p]:leading-relaxed">{description}</div>' if description else ''

    return f'''
    <div class="relative w-full rounded-lg border p-4 {variant_classes.get(variant, variant_classes['default'])}">
        {icon_html}
        <h5 class="mb-1 font-medium leading-none tracking-tight">{title}</h5>
        {desc_html}
    </div>
    '''
