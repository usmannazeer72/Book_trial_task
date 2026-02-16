"""
Create Sample Input Excel File using openpyxl (no pandas required)
"""

from openpyxl import Workbook
import os


# Sample book data as rows
rows = [
    [
        'title',
        'notes_on_outline_before',
        'notes_on_outline_after',
        'status_outline_notes'
    ],
    [
        'The Future of Artificial Intelligence',
        'Focus on practical applications, ethical considerations, and real-world case studies. Include chapters on machine learning, AI in healthcare, and future trends.',
        '',
        ''
    ],
    [
        'Sustainable Living: A Practical Guide',
        'Write for beginners. Include eco-friendly practices for home, work, and travel. Add actionable tips and cost-saving strategies.',
        '',
        ''
    ],
    [
        'Digital Marketing in 2026',
        'Cover social media trends, SEO strategies, content marketing, and AI tools for marketers. Include case studies from successful campaigns.',
        '',
        ''
    ]
]


def create_excel(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Books'

    for row in rows:
        ws.append(row)

    wb.save(path)


if __name__ == '__main__':
    output_path = 'input/books_input.xlsx'
    create_excel(output_path)
    print(f"✓ Sample Excel file created: {output_path}")
    print("\nSample data:")
    for r in rows[1:]:
        print(r)
