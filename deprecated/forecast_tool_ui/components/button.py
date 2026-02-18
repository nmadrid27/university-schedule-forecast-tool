"""
shadcn/ui Button Component
Generates HTML for buttons with shadcn styling
"""

def button(
    label: str,
    variant: str = "default",
    size: str = "default",
    onclick: str = None,
    icon: str = None,
    icon_position: str = "left",
    full_width: bool = False,
    disabled: bool = False
) -> str:
    """
    Generate shadcn-styled button HTML

    Args:
        label: Button text
        variant: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link'
        size: 'default' | 'sm' | 'lg' | 'icon'
        onclick: JavaScript onclick handler
        icon: Lucide icon name (e.g., 'download', 'check', 'x')
        icon_position: 'left' | 'right'
        full_width: If True, button spans full width
        disabled: If True, button is disabled

    Returns:
        HTML string for button
    """
    # Variant classes
    variant_classes = {
        'default': 'bg-primary text-primary-foreground hover:bg-primary/90',
        'destructive': 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        'outline': 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        'secondary': 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        'ghost': 'hover:bg-accent hover:text-accent-foreground',
        'link': 'text-primary underline-offset-4 hover:underline'
    }

    # Size classes
    size_classes = {
        'default': 'h-10 px-4 py-2',
        'sm': 'h-9 rounded-md px-3',
        'lg': 'h-11 rounded-md px-8',
        'icon': 'h-10 w-10'
    }

    # Base classes (shadcn button)
    base_classes = """
        inline-flex items-center justify-center rounded-md text-sm font-medium
        ring-offset-background transition-colors focus-visible:outline-none
        focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
        disabled:pointer-events-none disabled:opacity-50
    """.replace('\n', ' ').strip()

    # Build class string
    width_class = "w-full" if full_width else ""
    classes = f"{base_classes} {variant_classes.get(variant, variant_classes['default'])} {size_classes.get(size, size_classes['default'])} {width_class}"

    # Icon HTML
    icon_html = ""
    if icon:
        icon_size = "h-4 w-4"
        icon_margin = "mr-2" if icon_position == "left" and label else "ml-2" if icon_position == "right" and label else ""
        icon_html = f'<i data-lucide="{icon}" class="{icon_size} {icon_margin}"></i>'

    # Attributes
    onclick_attr = f'onclick="{onclick}"' if onclick else ''
    disabled_attr = 'disabled' if disabled else ''

    # Compose HTML
    if icon_position == "left":
        content = f"{icon_html}{label}"
    else:
        content = f"{label}{icon_html}"

    return f'''
    <button class="{classes}" {onclick_attr} {disabled_attr}>
        {content}
    </button>
    '''
