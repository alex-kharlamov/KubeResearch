from itertools import zip_longest

def join_tables_horizontally(table1, table2, separator=' ' * 4):
    t1_rows = table1.split('\n')
    t2_rows = table2.split('\n')

    max_rows = max(len(t1_rows), len(t2_rows))
    t1_max_width = max([len(row) for row in t1_rows])
    t2_max_width = max([len(row) for row in t2_rows])

    output = []
    for t1_row, t2_row in zip_longest(t1_rows, t2_rows, fillvalue=None):
        if t1_row is not None and t2_row is not None:
            output.append(f'{t1_row}{separator}{t2_row}')
        elif t1_row is None:
            output.append(f'{" " * t1_max_width}{separator}{t2_row}')
        elif t2_row is None:
            output.append(f'{t1_row}{separator}{" " * t2_max_width}')
    return '\n'.join(output)