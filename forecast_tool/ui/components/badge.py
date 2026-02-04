"""
shadcn/ui Badge Component
Generates HTML for badges/chips with shadcn styling
"""

def badge(
    label: str,
    variant: str = "default"
) -> str:
    """
    Generate shadcn-styled badge HTML

    Args:
        label: Badge text
        variant: 'default' | 'secondary' | 'destructive' | 'outline'

    Returns:
        HTML string for badge
    """
    # Variant classes
    variant_classes = {
        'default': 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        'secondary': 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        'destructive': 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        'outline': 'text-foreground'
    }

    # Base classes
    base_classes = """
        inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold
        transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
    """.replace('\n', ' ').strip()

    classes = f"{base_classes} {variant_classes.get(variant, variant_classes['default'])}"

    return f'<div class="{classes}">{label}</div>'
