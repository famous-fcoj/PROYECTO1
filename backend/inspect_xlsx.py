import pandas as pd
path = r"c:\Users\$$$$$$$$$$$$$$$$$$$$\Desktop\PROYECTO1\OT 2025 MECANICAS.xlsx"
print('Reading:', path)
try:
    xls = pd.ExcelFile(path)
    print('Sheets found:', xls.sheet_names)
    for name in xls.sheet_names:
        df = xls.parse(name, nrows=0)
        print(f'--- Sheet: {name} | columns ({len(df.columns)}):')
        for c in df.columns:
            print('   ', repr(str(c)))
except Exception as e:
    print('Error reading file:', e)
