"""
shadcn/ui Table Component
Generates HTML for tables with shadcn styling
"""

import pandas as pd
from typing import List, Optional


def table(
    df: pd.DataFrame,
    headers: Optional[List[str]] = None,
    caption: str = None,
    striped: bool = True
) -> str:
    """
    Generate shadcn-styled table HTML from DataFrame

    Args:
        df: Pandas DataFrame
        headers: Optional custom headers (defaults to column names)
        caption: Optional table caption
        striped: If True, alternating row backgrounds

    Returns:
        HTML string for table
    """
    if headers is None:
        headers = df.columns.tolist()

    # Table header
    header_cells = "".join([
        f'<th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">{h}</th>'
        for h in headers
    ])
    header_html = f'<thead class="[&_tr]:border-b"><tr>{header_cells}</tr></thead>'

    # Table body
    rows = []
    for idx, row in df.iterrows():
        cells = "".join([
            f'<td class="p-4 align-middle">{val}</td>'
            for val in row
        ])
        row_class = "border-b transition-colors hover:bg-muted/50"
        rows.append(f'<tr class="{row_class}">{cells}</tr>')

    body_html = f'<tbody class="[&_tr:last-child]:border-0">{"".join(rows)}</tbody>'

    # Caption
    caption_html = f'<caption class="mt-4 text-sm text-muted-foreground">{caption}</caption>' if caption else ''

    # Complete table
    return f'''
    <div class="relative w-full overflow-auto rounded-lg border bg-card shadow-sm">
        <table class="w-full caption-bottom text-sm">
            {caption_html}
            {header_html}
            {body_html}
        </table>
    </div>
    '''
